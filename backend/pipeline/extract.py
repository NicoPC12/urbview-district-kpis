"""Overture S3 → ``data/raw/*.parquet``: the slice of the pinned release the KPIs need.

This is the slow, network-bound step (``make extract``). It is scripted and committed; its
output is not. ``make load-data`` normally skips it by downloading the same files as a
release asset (see :mod:`pipeline.load_data`).

What is pulled, and why only this (Phase 0 evidence in ``docs/recon.md``):

============  ==================================================================================
type          reason / filter
============  ==================================================================================
district      one ``division_area`` row: ``subtype = 'macrohood'``, ``names.primary`` as pinned
segment       ``low_speed_street_share``, ``crossing_density``, ``pedestrian_network_share``,
              ``street_tree_density`` denominators; ``subtype = 'road'`` only (rail is never read)
infrastructure ``crossing_density``; all classes kept (small) so a live "add a KPI" has benches,
              signals and lamps available without a new pull
land_use      ``green_space_distance_p50`` targets; district bbox **plus 1.5 km** so buildings on
              the district edge see the park across the boundary
land          ``street_tree_density``; blanket ``land``/``physical`` polygons excluded (they cover
              the whole district and carry nothing)
building      ``green_space_distance_p50`` population (centroids are taken in the build)
============  ==================================================================================

Dropped entirely: ``connector``, ``water``, ``place``, ``building_part``, ``land_cover``,
``division``, ``division_boundary``, ``address`` — no chosen KPI reads them.

Columns are projected at read time (parquet column pruning over HTTP) and the ``bbox`` struct
is used for row-group pushdown. Files are written atomically and skipped when present, so
re-running is idempotent; delete ``data/raw`` to force a fresh pull.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb

from pipeline.release import OVERTURE_RELEASE, OVERTURE_S3_REGION, overture_path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

# Barcelona-wide bbox used only to find the district row; every other read uses the
# district's own bbox.
BCN_BBOX = (2.05, 41.32, 2.24, 41.47)
DISTRICT_NAME = "l'Eixample"
DISTRICT_SUBTYPE = "macrohood"  # Phase 0: Barcelona's districts are macrohoods, not boroughs

# Margin (metres) beyond the district bbox for green-space targets: a building at the edge
# must see the nearest park even when it lies outside the district.
GREEN_MARGIN_M = 1_500
# Degrees per metre at 41.4° N — only used to widen a bbox filter, never to measure.
DEG_PER_M_LAT = 1 / 111_320
DEG_PER_M_LON = 1 / (111_320 * 0.750)

# The subtypes Phase 0 identified as green in `land_use`.
GREEN_SUBTYPES = ("park", "horticulture", "managed", "recreation", "agriculture")


def log(message: str) -> None:
    """Flush-print so progress shows through ``docker compose exec``."""
    print(message, flush=True)


def connect() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with spatial + httpfs and anonymous access to the Overture bucket."""
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_region = '{OVERTURE_S3_REGION}'")
    return con


def bbox_predicate(bbox: tuple[float, float, float, float]) -> str:
    """SQL predicate on Overture's ``bbox`` struct for row-group pushdown."""
    xmin, ymin, xmax, ymax = bbox
    return (
        f"bbox.xmin < {xmax} AND bbox.xmax > {xmin} AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}"
    )


def widen(
    bbox: tuple[float, float, float, float], metres: float
) -> tuple[float, float, float, float]:
    """Grow a lon/lat bbox by roughly ``metres`` on every side (filter use only)."""
    xmin, ymin, xmax, ymax = bbox
    dx, dy = metres * DEG_PER_M_LON, metres * DEG_PER_M_LAT
    return (xmin - dx, ymin - dy, xmax + dx, ymax + dy)


def copy(con: duckdb.DuckDBPyConnection, name: str, select: str) -> float:
    """Run ``COPY (select) TO data/raw/<name>.parquet`` atomically. Returns seconds taken."""
    target = RAW_DIR / f"{name}.parquet"
    if target.exists():
        log(f"  {name}: cached")
        return 0.0
    tmp = target.with_suffix(".parquet.tmp")
    started = time.time()
    log(f"  {name}: pulling ...")
    con.execute(f"COPY ({select}) TO '{tmp.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    tmp.replace(target)
    seconds = time.time() - started
    log(f"  {name}: {target.stat().st_size / 1e6:.1f} MB in {seconds:.0f}s")
    return seconds


def extract_district(con: duckdb.DuckDBPyConnection) -> tuple[float, float, float, float]:
    """Pull the district polygon and return its lon/lat bbox."""
    name = DISTRICT_NAME.replace("'", "''")
    copy(
        con,
        "district",
        f"""
        SELECT id, names.primary AS name, subtype, geometry, bbox
        FROM read_parquet('{overture_path("divisions", "division_area")}')
        WHERE {bbox_predicate(BCN_BBOX)}
          AND subtype = '{DISTRICT_SUBTYPE}' AND names.primary = '{name}'
        """,
    )
    row = con.execute(
        f"SELECT bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax, count(*) OVER () "
        f"FROM read_parquet('{(RAW_DIR / 'district.parquet').as_posix()}')"
    ).fetchone()
    if row is None:
        raise SystemExit(
            f"district {DISTRICT_NAME!r} ({DISTRICT_SUBTYPE}) not found in the release"
        )
    if row[4] != 1:
        raise SystemExit(f"expected exactly one district row, got {row[4]}")
    return (float(row[0]), float(row[1]), float(row[2]), float(row[3]))


def extract_all(con: duckdb.DuckDBPyConnection) -> dict[str, float]:
    """Pull every needed type. Returns seconds per type (0 for cached)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}
    log(f"release {OVERTURE_RELEASE}")

    started = time.time()
    district_bbox = extract_district(con)
    timings["district"] = time.time() - started
    log(f"  district bbox {tuple(round(v, 4) for v in district_bbox)}")
    inside = bbox_predicate(district_bbox)
    green_bbox = bbox_predicate(widen(district_bbox, GREEN_MARGIN_M))

    timings["segment"] = copy(
        con,
        "segment",
        f"""
        SELECT id, names.primary AS name, subtype, class, subclass, speed_limits, geometry
        FROM read_parquet('{overture_path("transportation", "segment")}')
        WHERE {inside} AND subtype = 'road'
        """,
    )
    timings["infrastructure"] = copy(
        con,
        "infrastructure",
        f"""
        SELECT id, subtype, class, geometry
        FROM read_parquet('{overture_path("base", "infrastructure")}')
        WHERE {inside}
        """,
    )
    green = ", ".join(f"'{s}'" for s in GREEN_SUBTYPES)
    timings["land_use"] = copy(
        con,
        "land_use",
        f"""
        SELECT id, names.primary AS name, subtype, class, geometry
        FROM read_parquet('{overture_path("base", "land_use")}')
        WHERE {green_bbox} AND subtype IN ({green})
        """,
    )
    timings["land"] = copy(
        con,
        "land",
        f"""
        SELECT id, subtype, class, geometry
        FROM read_parquet('{overture_path("base", "land")}')
        WHERE {inside} AND subtype NOT IN ('land', 'physical')
        """,
    )
    timings["building"] = copy(
        con,
        "building",
        f"""
        SELECT id, subtype, class, geometry
        FROM read_parquet('{overture_path("buildings", "building")}')
        WHERE {inside}
        """,
    )
    return timings


def main() -> int:
    """Entry point for ``python -m pipeline.extract``."""
    started = time.time()
    timings = extract_all(connect())
    total_mb = sum(p.stat().st_size for p in RAW_DIR.glob("*.parquet")) / 1e6
    log(
        json.dumps(
            {
                "seconds": {k: round(v) for k, v in timings.items()},
                "total_seconds": round(time.time() - started),
                "total_mb": round(total_mb, 1),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
