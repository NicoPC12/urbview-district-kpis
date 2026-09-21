"""Turn a request area (district slug | bbox | GeoJSON polygon) into one validated polygon.

No geometry maths here: parsing, validity, area and the district-overlap measure are all
DuckDB calls through :mod:`warehouse.area`. This module decides what is acceptable and
phrases the refusal.

A polygon outside the loaded district is *not* refused (the brief says "draw anywhere"): it
resolves with ``district_overlap_share = 0`` and every KPI answers ``sample_size = 0``. What
is refused, as a 422 at the API: invalid geometry, too many vertices, too large an area.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import duckdb

from warehouse import area as warehouse_area

# Reject polygons larger than this: a whole-city polygon would be a denial-of-service on a
# per-request engine, and the product is about districts and parts of districts.
MAX_AREA_KM2 = 50.0

# A hand-drawn polygon has tens of vertices; thousands is a pasted coastline, and every
# ST_Intersection in every KPI would pay for it.
MAX_VERTICES = 2_000


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
class DistrictRef:
    """A catalogue entry: the slug the API accepts and the warehouse row it names."""

    slug: str
    overture_id: str


@dataclass(frozen=True)
class ResolvedArea:
    """A polygon the engine may run on."""

    name: str
    wkt: str
    """EPSG:4326 WKT, normalised by DuckDB."""
    area_m2: float
    source: AreaSource
    district_overlap_share: float
    """0–1: how much of the polygon's area lies inside the loaded district (where data is)."""

    @property
    def km2(self) -> float:
        """Area in square kilometres."""
        return self.area_m2 / 1e6


class InvalidAreaError(ValueError):
    """The request area cannot be used; ``str(exc)`` is safe to show the client."""


def _candidate_wkt(
    con: duckdb.DuckDBPyConnection, request: AreaRequest, districts: Mapping[str, DistrictRef]
) -> tuple[str, str, AreaSource]:
    """(name, WKT, source) before validation."""
    if request.district is not None:
        slug = request.district.strip().lower()
        ref = districts.get(slug)
        if ref is None:
            raise InvalidAreaError(
                f"unknown district {request.district!r}; known: {sorted(districts)}"
            )
        try:
            name, wkt, _ = warehouse_area.district_wkt(con, ref.overture_id)
        except LookupError as exc:
            raise InvalidAreaError(f"district {slug!r} is not in the warehouse") from exc
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


def resolve(
    con: duckdb.DuckDBPyConnection,
    request: AreaRequest,
    districts: Mapping[str, DistrictRef],
) -> ResolvedArea:
    """Validate the request area against the warehouse.

    Args:
        con: a warehouse cursor.
        request: district slug, bbox or polygon.
        districts: the catalogue (slug -> warehouse row), loaded by the caller.

    Raises:
        InvalidAreaError: invalid geometry (self-intersecting, unclosed), too many vertices,
            oversized, or an unknown district slug.
    """
    name, wkt, source = _candidate_wkt(con, request, districts)
    try:
        check = warehouse_area.inspect_area(con, wkt)
    except duckdb.Error as exc:
        raise InvalidAreaError(f"geometry could not be parsed: {exc}") from exc
    if not check.is_valid:
        raise InvalidAreaError("polygon is not valid (self-intersecting or degenerate)")
    if check.n_points > MAX_VERTICES:
        raise InvalidAreaError(
            f"polygon has {check.n_points:,} vertices; the maximum is {MAX_VERTICES:,}"
        )
    if check.area_m2 <= 0:
        raise InvalidAreaError("polygon has no area")
    if check.area_m2 > MAX_AREA_KM2 * 1e6:
        raise InvalidAreaError(
            f"polygon is {check.area_m2 / 1e6:.1f} km2; the maximum is {MAX_AREA_KM2:.0f} km2"
        )
    return ResolvedArea(
        name=name,
        wkt=check.wkt,
        area_m2=check.area_m2,
        source=source,
        district_overlap_share=check.district_overlap_share,
    )
