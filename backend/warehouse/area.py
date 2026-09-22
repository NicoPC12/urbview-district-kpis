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

import json
from dataclasses import dataclass
from typing import Any

import duckdb

from warehouse.connection import SESSION_PATH, transform_to_m


@dataclass(frozen=True)
class AreaCheck:
    """What the warehouse can say about a candidate polygon before any KPI runs."""

    wkt: str
    """Normalised EPSG:4326 WKT (as DuckDB re-serialises it)."""
    is_valid: bool
    area_m2: float
    n_points: int
    district_overlap_share: float
    """Share (0–1) of the polygon's area that lies inside the loaded district. The warehouse
    only holds features there, so this is the share of the drawing that has data."""
    effective_wkt: str
    """The polygon ∩ the district, EPSG:4326 WKT: what every KPI and layer is measured on.
    The warehouse keeps whole geometries of features that *touch* the district, so clipping
    to the drawn polygon alone would count the parts outside the district. Equals ``wkt``
    when the polygon lies inside the district; empty when it lies entirely outside."""


def inspect_area(con: duckdb.DuckDBPyConnection, wkt_4326: str) -> AreaCheck:
    """Validate a polygon and measure it in metres, without registering it.

    Invalid geometry (self-intersection, unclosed ring) yields ``is_valid = False`` with
    ``area_m2 = 0``; a WKT that does not parse at all raises ``duckdb.Error`` for the caller to
    turn into a 422.
    """
    row = con.execute(
        f"""
        WITH g AS (
            SELECT geom, CASE WHEN ST_IsValid(geom) THEN {transform_to_m("geom")} END AS geom_m
            FROM (SELECT ST_GeomFromText(?) AS geom)
        )
        SELECT ST_AsText(g.geom),
               ST_IsValid(g.geom),
               coalesce(ST_Area(g.geom_m), 0),
               ST_NPoints(g.geom),
               coalesce(
                   (SELECT sum(ST_Area(ST_Intersection(d.geom_m, g.geom_m))) FROM district d)
                   / nullif(ST_Area(g.geom_m), 0),
                   0
               ),
               -- Polygon parts only: two boundaries touching along an edge would otherwise
               -- leave a line in a GEOMETRYCOLLECTION. Clipping is topological, so 4326 is
               -- fine here; every metre is still measured on geom_m downstream.
               CASE WHEN ST_IsValid(g.geom) THEN ST_AsText(ST_CollectionExtract(
                   ST_Intersection(g.geom, (SELECT ST_Union_Agg(geom) FROM district)), 3
               )) END
        FROM g
        """,
        [wkt_4326],
    ).fetchone()
    assert row is not None  # noqa: S101 - one-row CTE
    return AreaCheck(
        wkt=str(row[0]),
        is_valid=bool(row[1]),
        area_m2=float(row[2]),
        n_points=int(row[3]),
        district_overlap_share=min(1.0, float(row[4])),
        effective_wkt="" if row[5] is None else str(row[5]),
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
    con.execute(SESSION_PATH.read_text(encoding="utf-8"))  # shared per-request definitions


def district_wkt(con: duckdb.DuckDBPyConnection, district_id: str) -> tuple[str, str, float]:
    """(name, EPSG:4326 WKT, area_m2) of one loaded district by Overture id.

    Raises:
        LookupError: the warehouse holds no district with that id.
    """
    row = con.execute(
        "SELECT name, ST_AsText(geom), area_m2 FROM district WHERE id = ?", [district_id]
    ).fetchone()
    if row is None:
        raise LookupError(f"warehouse has no district with id {district_id!r}")
    return str(row[0]), str(row[1]), float(row[2])


def district_outline(con: duckdb.DuckDBPyConnection, district_id: str) -> dict[str, Any]:
    """``{km2, bbox, geometry}`` of one district for the map: outline at 5 decimals, bbox."""
    row = con.execute(
        """
        SELECT area_m2 / 1e6,
               [ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom)],
               ST_AsGeoJSON(ST_ReducePrecision(geom, 0.00001))
        FROM district WHERE id = ?
        """,
        [district_id],
    ).fetchone()
    if row is None:
        raise LookupError(f"warehouse has no district with id {district_id!r}")
    return {
        "km2": float(row[0]),
        "bbox": [float(v) for v in row[1]],
        "geometry": json.loads(row[2]),
    }
