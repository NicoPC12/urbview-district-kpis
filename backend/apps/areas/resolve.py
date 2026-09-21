"""Turn a request area (district slug | bbox | GeoJSON polygon) into one validated polygon.

No geometry maths here: parsing, validity, area and the district-intersection check are all
DuckDB calls through :mod:`warehouse.area`. This module decides what is acceptable and
phrases the refusal.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import duckdb

from warehouse import area as warehouse_area

# Reject polygons larger than this: a whole-city polygon would be a denial-of-service on a
# per-request engine, and the product is about districts and parts of districts.
MAX_AREA_KM2 = 50.0

# District slug -> the name the warehouse row carries. Phase 4 moves this to the District
# model in Postgres; the warehouse holds exactly one district today.
KNOWN_DISTRICTS: dict[str, str] = {"eixample": "l'Eixample"}


class AreaSource(StrEnum):
    """How the area was specified."""

    DISTRICT = "district"
    BBOX = "bbox"
    DRAWN = "drawn"


@dataclass(frozen=True)
class AreaRequest:
    """Exactly one of the three must be set (the API layer enforces the count)."""

    district: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    polygon: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResolvedArea:
    """A polygon the engine may run on."""

    name: str
    wkt: str
    """EPSG:4326 WKT, normalised by DuckDB."""
    area_m2: float
    source: AreaSource

    @property
    def km2(self) -> float:
        """Area in square kilometres."""
        return self.area_m2 / 1e6


class InvalidAreaError(ValueError):
    """The request area cannot be used; ``str(exc)`` is safe to show the client."""


def _candidate_wkt(
    con: duckdb.DuckDBPyConnection, request: AreaRequest
) -> tuple[str, str, AreaSource]:
    """(name, WKT, source) before validation."""
    if request.district is not None:
        slug = request.district.strip().lower()
        if slug not in KNOWN_DISTRICTS:
            raise InvalidAreaError(
                f"unknown district {request.district!r}; known: {sorted(KNOWN_DISTRICTS)}"
            )
        name, wkt, _ = warehouse_area.district_wkt(con)
        return name, wkt, AreaSource.DISTRICT
    if request.bbox is not None:
        xmin, ymin, xmax, ymax = request.bbox
        if not (xmin < xmax and ymin < ymax):
            raise InvalidAreaError(
                "bbox must be [xmin, ymin, xmax, ymax] with xmin < xmax and ymin < ymax"
            )
        wkt = (
            f"POLYGON(({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))"
        )
        return "Bounding box", wkt, AreaSource.BBOX
    if request.polygon is not None:
        if request.polygon.get("type") != "Polygon":
            raise InvalidAreaError("polygon must be a GeoJSON Polygon")
        try:
            row = con.execute(
                "SELECT ST_AsText(ST_GeomFromGeoJSON(?))", [json.dumps(request.polygon)]
            ).fetchone()
        except duckdb.Error as exc:
            raise InvalidAreaError(f"polygon could not be parsed: {exc}") from exc
        assert row is not None  # noqa: S101 - scalar select
        return "Drawn area", str(row[0]), AreaSource.DRAWN
    raise InvalidAreaError("one of district, bbox or polygon is required")


def resolve(con: duckdb.DuckDBPyConnection, request: AreaRequest) -> ResolvedArea:
    """Validate the request area against the warehouse.

    Raises:
        InvalidAreaError: invalid geometry (self-intersecting, unclosed), oversized, or not
            touching the loaded district.
    """
    name, wkt, source = _candidate_wkt(con, request)
    try:
        check = warehouse_area.inspect_area(con, wkt)
    except duckdb.Error as exc:
        raise InvalidAreaError(f"geometry could not be parsed: {exc}") from exc
    if not check.is_valid:
        raise InvalidAreaError("polygon is not valid (self-intersecting or degenerate)")
    if check.area_m2 <= 0:
        raise InvalidAreaError("polygon has no area")
    if check.area_m2 > MAX_AREA_KM2 * 1e6:
        raise InvalidAreaError(
            f"polygon is {check.area_m2 / 1e6:.1f} km2; the maximum is {MAX_AREA_KM2:.0f} km2"
        )
    if not check.intersects_district:
        raise InvalidAreaError(
            f"polygon does not touch the loaded district ({check.district_name})"
        )
    return ResolvedArea(name=name, wkt=check.wkt, area_m2=check.area_m2, source=source)
