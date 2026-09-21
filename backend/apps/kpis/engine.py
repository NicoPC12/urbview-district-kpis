"""Run the registry over a resolved area and assemble the response.

Orchestration only: resolve → register the area once → run each KPI's SQL → run its layers →
insights → legend. No SQL strings and no geometry maths live here (CLAUDE.md §4).
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import duckdb

from apps.areas.resolve import AreaRequest, ResolvedArea, resolve
from apps.kpis import insights as insight_rules
from apps.kpis.registry import DEFAULT_COLOR, KPIS, REGISTRY_VERSION, KpiDefinition
from warehouse import area as warehouse_area
from warehouse import connection as warehouse_connection
from warehouse import kpi as warehouse_kpi


@dataclass(frozen=True)
class KpiResult:
    """One KPI's definition, its numbers for this area, and how long it took."""

    definition: KpiDefinition
    row: warehouse_kpi.KpiRow
    band: str | None
    computed_ms: float

    @property
    def key(self) -> str:
        """The KPI key, for lookups."""
        return self.definition.key


@dataclass(frozen=True)
class Layer:
    """A GeoJSON FeatureCollection explaining one KPI on the map."""

    id: str
    kpi_key: str
    features: tuple[dict[str, Any], ...]
    computed_ms: float


@dataclass(frozen=True)
class LegendItem:
    """One category of one KPI's map layer."""

    kpi_key: str
    key: str
    label: str
    color: str


@dataclass(frozen=True)
class Meta:
    """Provenance and timing."""

    computed_ms: float
    cached: bool
    overture_release: str
    registry_version: str
    timings_ms: Mapping[str, float]


@dataclass(frozen=True)
class KpiResponse:
    """The whole answer for one area. Serialised as-is by the API layer."""

    area: ResolvedArea
    kpis: tuple[KpiResult, ...]
    layers: tuple[Layer, ...]
    insights: tuple[str, ...]
    legend: tuple[LegendItem, ...]
    meta: Meta


def compute(
    warehouse_path: Path,
    request: AreaRequest,
    *,
    definitions: tuple[KpiDefinition, ...] = KPIS,
    with_layers: bool = True,
) -> KpiResponse:
    """Compute every KPI for the request area.

    Args:
        warehouse_path: the DuckDB file built by ``make load-data``.
        request: district slug, bbox or polygon.
        definitions: the registry (tests pass a subset).
        with_layers: skip the GeoJSON layers (tests and timing runs).

    Raises:
        InvalidAreaError: from :func:`apps.areas.resolve.resolve`.
        WarehouseMissingError: the warehouse has not been built.
    """
    started = time.perf_counter()
    con = warehouse_connection.connect(warehouse_path)
    try:
        area = resolve(con, request)
        warehouse_area.register_area(con, area.wkt)  # once per request, not once per KPI
        return _compute_on(con, area, definitions, with_layers, started)
    finally:
        con.close()


def _compute_on(
    con: duckdb.DuckDBPyConnection,
    area: ResolvedArea,
    definitions: tuple[KpiDefinition, ...],
    with_layers: bool,
    started: float,
) -> KpiResponse:
    timings: dict[str, float] = {}
    results: list[KpiResult] = []
    layers: list[Layer] = []
    for definition in definitions:
        t0 = time.perf_counter()
        row = warehouse_kpi.run_kpi(con, definition.sql)
        ms = (time.perf_counter() - t0) * 1000
        timings[definition.key] = round(ms, 1)
        results.append(KpiResult(definition, row, definition.band_for(row.value), ms))
        if with_layers:
            for layer_def in definition.layers:
                t0 = time.perf_counter()
                features = tuple(warehouse_kpi.run_layer(con, layer_def.sql))
                ms = (time.perf_counter() - t0) * 1000
                timings[f"layer:{layer_def.id}"] = round(ms, 1)
                layers.append(Layer(layer_def.id, definition.key, features, ms))

    release = _meta_value(con, "overture_release")
    kpis = tuple(results)
    return KpiResponse(
        area=area,
        kpis=kpis,
        layers=tuple(layers),
        insights=tuple(insight_rules.generate(kpis, area)),
        legend=legend_for(kpis),
        meta=Meta(
            computed_ms=round((time.perf_counter() - started) * 1000, 1),
            cached=False,
            overture_release=release,
            registry_version=REGISTRY_VERSION,
            timings_ms=MappingProxyType(timings),
        ),
    )


def compute_with_connection(
    con: duckdb.DuckDBPyConnection,
    area: ResolvedArea,
    definitions: tuple[KpiDefinition, ...] = KPIS,
    *,
    with_layers: bool = True,
) -> KpiResponse:
    """Test entry point: run on an already-open connection with the area registered."""
    return _compute_on(con, area, definitions, with_layers, started=time.perf_counter())


def legend_for(results: tuple[KpiResult, ...]) -> tuple[LegendItem, ...]:
    """Every breakdown category (and single-category layers) with its colour."""
    items: list[LegendItem] = []
    for result in results:
        definition = result.definition
        if result.row.breakdown:
            for item in result.row.breakdown:
                items.append(
                    LegendItem(
                        definition.key,
                        item.key,
                        item.label,
                        definition.colors.get(item.key, DEFAULT_COLOR),
                    )
                )
        else:
            for key, color in definition.colors.items():
                items.append(LegendItem(definition.key, key, key.replace("_", " "), color))
    return tuple(items)


def _meta_value(con: duckdb.DuckDBPyConnection, key: str) -> str:
    row = con.execute("SELECT value FROM meta WHERE key = ?", [key]).fetchone()
    return "" if row is None else str(row[0])
