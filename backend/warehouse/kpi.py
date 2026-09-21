"""Run one KPI query or one layer query against a connection with a registered area.

The SQL contract (CLAUDE.md §8): a KPI file returns exactly one row with ``value``,
``sample_size``, ``breakdown`` (list of struct or NULL) and ``context`` (list of struct). A
layer file returns one JSON Feature per row. This module turns those rows into frozen value
objects and never touches geometry itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class BreakdownItem:
    """One slice of a KPI's breakdown (a chart bar, a map category)."""

    key: str
    label: str
    value: float


@dataclass(frozen=True)
class ContextItem:
    """A figure the reader needs to interpret the value but which is not itself a KPI."""

    key: str
    label: str
    value: float | None
    unit: str


@dataclass(frozen=True)
class KpiRow:
    """The one row a KPI query returns."""

    value: float | None
    sample_size: int
    breakdown: tuple[BreakdownItem, ...] | None
    context: tuple[ContextItem, ...]


class ContractError(RuntimeError):
    """A KPI query did not honour the one-row / four-column contract."""


def run_kpi(con: duckdb.DuckDBPyConnection, sql_path: Path) -> KpiRow:
    """Execute a KPI file (the ``area`` table and ``area_m()`` must already be registered)."""
    cur = con.execute(sql_path.read_text(encoding="utf-8"))
    columns = [d[0] for d in cur.description or []]
    rows = cur.fetchall()
    if len(rows) != 1:
        raise ContractError(f"{sql_path.name}: expected exactly one row, got {len(rows)}")
    if columns != ["value", "sample_size", "breakdown", "context"]:
        raise ContractError(
            f"{sql_path.name}: columns {columns} != value/sample_size/breakdown/context"
        )
    value, sample_size, breakdown, context = rows[0]
    return KpiRow(
        value=None if value is None else float(value),
        sample_size=int(sample_size),
        breakdown=None
        if breakdown is None
        else tuple(
            BreakdownItem(str(b["key"]), str(b["label"]), float(b["value"])) for b in breakdown
        ),
        context=tuple(
            ContextItem(
                str(c["key"]),
                str(c["label"]),
                None if c["value"] is None else float(c["value"]),
                str(c["unit"]),
            )
            for c in context
        ),
    )


def run_layer(con: duckdb.DuckDBPyConnection, sql_path: Path) -> list[dict[str, Any]]:
    """Execute a layer file and return its GeoJSON Features (already serialised by DuckDB)."""
    rows = con.execute(sql_path.read_text(encoding="utf-8")).fetchall()
    return [json.loads(row[0]) for row in rows]
