"""Builders for a tiny, hand-checkable warehouse.

Geometry is written in EPSG:25831 metres on a local grid whose origin sits inside Eixample
(so the derived EPSG:4326 coordinates are real Barcelona coordinates), and ``geom`` is
derived with ``ST_Transform(..., always_xy := true)`` exactly as the production build does.
The district is a 2 km square. Every helper takes plain metres so a test reads like the
sketch it came from: "two 100 m segments, one at 30 km/h".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from apps.areas.resolve import AreaRequest, ResolvedArea, resolve
from warehouse import area as warehouse_area
from warehouse.connection import SCHEMA_PATH, connect_memory, transform_to_deg

# Local origin in EPSG:25831 (metres); (0, 0) on the grid is this point.
X0, Y0 = 430_000.0, 4_582_000.0
DISTRICT_SIZE_M = 2_000.0

NON_CARRIAGEWAY = ("footway", "steps", "path", "cycleway", "pedestrian")
PEDESTRIAN = ("footway", "pedestrian", "steps", "path")


def box_wkt_m(xmin: float, ymin: float, xmax: float, ymax: float) -> str:
    """Axis-aligned rectangle in grid metres as EPSG:25831 WKT."""
    a, b, c, d = X0 + xmin, Y0 + ymin, X0 + xmax, Y0 + ymax
    return f"POLYGON(({a} {b}, {c} {b}, {c} {d}, {a} {d}, {a} {b}))"


def line_wkt_m(x1: float, y1: float, x2: float, y2: float) -> str:
    """Straight segment in grid metres as EPSG:25831 WKT."""
    return f"LINESTRING({X0 + x1} {Y0 + y1}, {X0 + x2} {Y0 + y2})"


def point_wkt_m(x: float, y: float) -> str:
    """Point in grid metres as EPSG:25831 WKT."""
    return f"POINT({X0 + x} {Y0 + y})"


def _create_file(path: Path) -> duckdb.DuckDBPyConnection:
    """A new, empty warehouse file with the production schema (what build.py produces)."""
    con = duckdb.connect(str(path))
    con.execute("LOAD spatial")
    con.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    return con


def geoms(wkt_m: str) -> str:
    """SQL producing ``(geom, geom_m)`` from a metric WKT literal (already validated input)."""
    m = f"ST_GeomFromText('{wkt_m}')"
    return f"{transform_to_deg(m)}, {m}"


class SyntheticWarehouse:
    """An in-memory warehouse with the production schema and a 2 km square district.

    Pass a not-yet-existing ``path`` to build a real file instead (for tests of the
    process-wide handle, which needs a file to ``stat``); ``close()`` it before a reader opens it.
    """

    DISTRICT_ID = "district-1"

    def __init__(self, path: Path | None = None) -> None:
        self.con: duckdb.DuckDBPyConnection = (
            connect_memory() if path is None else _create_file(path)
        )
        self._n = 0
        district = box_wkt_m(0, 0, DISTRICT_SIZE_M, DISTRICT_SIZE_M)
        self.con.execute(
            f"INSERT INTO district SELECT '{self.DISTRICT_ID}', 'Test district', "
            f"{geoms(district)}, ST_Area(ST_GeomFromText('{district}'))"
        )
        self.con.execute("INSERT INTO meta VALUES ('overture_release', 'synthetic')")
        self.con.execute("INSERT INTO meta VALUES ('built_at', ?)", [datetime.now(UTC).isoformat()])

    def close(self) -> None:
        """Release the file so another connection can open it read-only."""
        self.con.close()

    def _id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}-{self._n}"

    def segment(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        cls: str = "residential",
        speed: int | None = None,
        name: str | None = None,
    ) -> str:
        """A straight road segment; ``speed`` None means no mapped limit."""
        sid = self._id("seg")
        wkt = line_wkt_m(x1, y1, x2, y2)
        self.con.execute(
            f"""
            INSERT INTO segments
            SELECT ?, ?, ?, NULL, ?, ?, ?, ?, ST_Length(ST_GeomFromText('{wkt}')), {geoms(wkt)}
            """,
            [
                sid,
                name,
                cls,
                cls not in NON_CARRIAGEWAY,
                cls in PEDESTRIAN,
                speed,
                speed is not None,
            ],
        )
        return sid

    def crossing(self, x: float, y: float) -> str:
        """A crossing point."""
        cid = self._id("cross")
        self.con.execute(f"INSERT INTO crossings SELECT ?, {geoms(point_wkt_m(x, y))}", [cid])
        return cid

    def tree(self, x: float, y: float) -> str:
        """A tree point."""
        tid = self._id("tree")
        self.con.execute(f"INSERT INTO trees SELECT ?, {geoms(point_wkt_m(x, y))}", [tid])
        return tid

    def building(self, x: float, y: float) -> str:
        """A building centroid."""
        bid = self._id("bld")
        self.con.execute(
            f"INSERT INTO buildings SELECT ?, 'residential', NULL, {geoms(point_wkt_m(x, y))}",
            [bid],
        )
        return bid

    def green(self, xmin: float, ymin: float, xmax: float, ymax: float) -> str:
        """A rectangular green space; ``is_who_size`` follows from its area (>= 5,000 m2)."""
        gid = self._id("green")
        wkt = box_wkt_m(xmin, ymin, xmax, ymax)
        self.con.execute(
            f"""
            INSERT INTO green_spaces
            SELECT ?, ?, 'park', 'park', ST_Area(ST_GeomFromText('{wkt}')),
                   ST_Area(ST_GeomFromText('{wkt}')) >= 5000, {geoms(wkt)}
            """,
            [gid, gid],
        )
        return gid

    def area(self, xmin: float, ymin: float, xmax: float, ymax: float) -> ResolvedArea:
        """Resolve and register a rectangular request area given in grid metres."""
        polygon = self.geojson(box_wkt_m(xmin, ymin, xmax, ymax))
        resolved = resolve(self.con, AreaRequest(polygon=polygon), {})
        warehouse_area.register_area(self.con, resolved.effective_wkt)
        return resolved

    def geojson(self, wkt_m: str) -> dict[str, Any]:
        """GeoJSON (EPSG:4326) of a metric WKT, the way a client would send it."""
        row = self.con.execute(
            f"SELECT ST_AsGeoJSON({transform_to_deg('ST_GeomFromText(?)')})", [wkt_m]
        ).fetchone()
        assert row is not None
        return dict(json.loads(row[0]))
