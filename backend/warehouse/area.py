"""The request area: validation, and registration as the ``area`` temp table.

Every KPI query joins against ``area`` (one row: ``geom`` in EPSG:4326, ``geom_m`` in
EPSG:25831). It is created once per request so the polygon is projected once, not once per
KPI.

Index note (verified with EXPLAIN against the real warehouse, Phase 3): DuckDB uses an
R-tree only when the predicate argument is constant at plan time. A join against the ``area``
table plans as a SPATIAL_JOIN (13.5 ms on the district); a constant plans as
RTREE_INDEX_SCAN (4–5 ms). So :func:`register_area` also stores the metric polygon in a
session variable (bound as a parameter, never interpolated) and defines the scalar macro
``area_m()`` over it, which the planner folds to a constant. KPI queries use ``area_m()`` in
every ``ST_Intersects`` / ``ST_Intersection`` and read the ``area`` table only for metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from warehouse.connection import transform_to_m


@dataclass(frozen=True)
class AreaCheck:
    """What the warehouse can say about a candidate polygon before any KPI runs."""

    wkt: str
    """Normalised EPSG:4326 WKT (as DuckDB re-serialises it)."""
    is_valid: bool
    area_m2: float
    intersects_district: bool
    district_name: str


def inspect_area(con: duckdb.DuckDBPyConnection, wkt_4326: str) -> AreaCheck:
    """Validate a polygon and measure it in metres, without registering it.

    Invalid geometry (self-intersection, unclosed ring) yields ``is_valid = False`` with
    ``area_m2 = 0``; a WKT that does not parse at all raises ``duckdb.Error`` for the caller to
    turn into a 422.
    """
    row = con.execute(
        f"""
        WITH g AS (SELECT ST_GeomFromText(?) AS geom)
        SELECT ST_AsText(geom),
               ST_IsValid(geom),
               CASE WHEN ST_IsValid(geom) THEN ST_Area({transform_to_m("geom")}) ELSE 0 END,
               (SELECT bool_or(ST_Intersects(d.geom, g.geom)) FROM district d),
               (SELECT any_value(name) FROM district)
        FROM g
        """,
        [wkt_4326],
    ).fetchone()
    assert row is not None  # noqa: S101 - one-row CTE
    return AreaCheck(
        wkt=str(row[0]),
        is_valid=bool(row[1]),
        area_m2=float(row[2]),
        intersects_district=bool(row[3]),
        district_name=str(row[4]),
    )


def register_area(con: duckdb.DuckDBPyConnection, wkt_4326: str) -> None:
    """Create the one-row ``area`` temp table and the constant ``area_m()`` macro.

    Args:
        con: connection for this request.
        wkt_4326: a polygon already passed through :func:`inspect_area` (valid, normalised).
    """
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE area AS
        SELECT geom, {transform_to_m("geom")} AS geom_m,
               ST_Area({transform_to_m("geom")}) AS area_m2
        FROM (SELECT ST_GeomFromText(?) AS geom)
        """,
        [wkt_4326],
    )
    row = con.execute("SELECT ST_AsText(geom_m) FROM area").fetchone()
    assert row is not None  # noqa: S101 - the table was just created with one row
    con.execute("SET VARIABLE area_wkt_m = ?", [str(row[0])])
    con.execute(
        "CREATE OR REPLACE TEMP MACRO area_m() AS ST_GeomFromText(getvariable('area_wkt_m'))"
    )


def district_wkt(con: duckdb.DuckDBPyConnection) -> tuple[str, str, float]:
    """(name, EPSG:4326 WKT, area_m2) of the loaded district."""
    row = con.execute("SELECT name, ST_AsText(geom), area_m2 FROM district").fetchone()
    if row is None:
        raise LookupError("warehouse has no district row")
    return str(row[0]), str(row[1]), float(row[2])
