"""Run the KPI list over a resolved area and assemble the response.

Orchestration only: register the area once → run each KPI's SQL → run its layers → insights →
legend. No SQL strings and no geometry maths live here (CLAUDE.md §4). The caller owns the
cursor (one per request, see :mod:`warehouse.connection`) and the KPI list (one database
query, see :mod:`apps.kpis.definitions`).
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import duckdb

from apps.areas.resolve import ResolvedArea
from apps.kpis import insights as insight_rules
from apps.kpis.registry import DEFAULT_COLOR, Kpi
from warehouse import area as warehouse_area
from warehouse import connection as warehouse_connection
from warehouse import kpi as warehouse_kpi


@dataclass(frozen=True)
class KpiResult:
    """One KPI's definition, its numbers for this area, and how long it took."""

    definition: Kpi
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
    warehouse_build: str
    """First 12 hex digits of the warehouse build hash (the cache key ingredient)."""
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
    con: duckdb.DuckDBPyConnection,
    area: ResolvedArea,
    kpis: tuple[Kpi, ...],
    *,
    with_layers: bool = True,
) -> KpiResponse:
    """Compute every KPI for an already-resolved area on a request-private cursor.

    Args:
        con: this request's cursor (nothing else may run on it concurrently).
        area: validated by :func:`apps.areas.resolve.resolve`.
        kpis: the KPI list for this request (tests pass a subset).
        with_layers: skip the GeoJSON layers (tests and timing runs).
    """
    started = time.perf_counter()
    # Once per request, not once per KPI — and on the drawn ∩ district polygon, never on
    # the raw drawing (segments that touch the district are stored whole).
    warehouse_area.register_area(con, area.effective_wkt)
    timings: dict[str, float] = {}
    results: list[KpiResult] = []
    layers: list[Layer] = []
    for definition in kpis:
        t0 = time.perf_counter()
        row = warehouse_kpi.run_kpi(con, definition.spec.sql)
        ms = (time.perf_counter() - t0) * 1000
        timings[definition.key] = round(ms, 1)
        results.append(KpiResult(definition, row, definition.band_for(row.value), ms))
        if with_layers:
            for layer_def in definition.spec.layers:
                t0 = time.perf_counter()
                features = tuple(warehouse_kpi.run_layer(con, layer_def.sql))
                ms = (time.perf_counter() - t0) * 1000
                timings[f"layer:{layer_def.id}"] = round(ms, 1)
                layers.append(Layer(layer_def.id, definition.key, features, ms))

    info = warehouse_connection.read_info(con)
    kpi_results = tuple(results)
    return KpiResponse(
        area=area,
        kpis=kpi_results,
        layers=tuple(layers),
        insights=tuple(insight_rules.generate(kpi_results, area)),
        legend=legend_for(kpi_results),
        meta=Meta(
            computed_ms=round((time.perf_counter() - started) * 1000, 1),
            cached=False,
            overture_release=info.overture_release,
            warehouse_build=info.build_hash[:12],
            timings_ms=MappingProxyType(timings),
        ),
    )


def legend_for(results: tuple[KpiResult, ...]) -> tuple[LegendItem, ...]:
    """Every breakdown category (and single-category layers) with its colour."""
    items: list[LegendItem] = []
    for result in results:
        definition = result.definition
        colors = definition.spec.colors
        if result.row.breakdown:
            for item in result.row.breakdown:
                items.append(
                    LegendItem(
                        definition.key, item.key, item.label, colors.get(item.key, DEFAULT_COLOR)
                    )
                )
        else:
            for key, color in colors.items():
                items.append(LegendItem(definition.key, key, key.replace("_", " "), color))
    return tuple(items)
