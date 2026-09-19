"""``data/raw/*.parquet`` → ``data/warehouse.duckdb``: the tables the KPI SQL reads.

Everything geometric happens in DuckDB SQL; Python only sequences the statements. Each
table stores ``geom`` (EPSG:4326, for serving GeoJSON) and ``geom_m`` (EPSG:25831, for every
metre) and gets an R-tree index on ``geom_m``. Every transform passes ``always_xy := true``
(CLAUDE.md rule 9).

Only what the five KPIs need is loaded (see ``docs/recon.md`` Part 6 and ``NOTES.md``):

- ``district``      the one polygon, with its area
- ``segments``      road segments intersecting the district, with the derived flags the
                    KPIs filter on (carriageway / pedestrian / posted speed) precomputed
- ``crossings``     ``infrastructure`` points, ``class = 'crossing'``
- ``green_spaces``  green ``land_use`` polygons within 1.5 km of the district bbox, with area
                    and the WHO ≥ 0.5 ha flag
- ``buildings``     building centroids (population for the distance KPI)
- ``trees``         ``land`` points, ``class = 'tree'``
- ``meta``          release, build time, source checksums

Tables are created from ``warehouse/schema.sql`` — the same DDL the test fixtures use — and
then filled with ``INSERT ... SELECT``. Rebuilding is idempotent: the file is written to a
temporary path and swapped in.
``access_restrictions`` is deliberately not loaded — no KPI reads it, and Phase 0 showed its
dominant entry is a one-way rule that naive logic misreads as a closure (NOTES.md).
"""

from __future__ import annotations

import hashlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from pipeline.release import OVERTURE_RELEASE

BACKEND_DIR = Path(__file__).resolve().parent.parent
SCHEMA = BACKEND_DIR / "warehouse" / "schema.sql"
DATA_DIR = BACKEND_DIR.parent / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE = DATA_DIR / "warehouse.duckdb"

DEG_CRS = "EPSG:4326"
M_CRS = "EPSG:25831"

# Classes that carry vehicle traffic. Everything else under subtype='road' is pedestrian or
# cycle infrastructure. Used by every "per km of carriageway" denominator.
NON_CARRIAGEWAY_CLASSES = ("footway", "steps", "path", "cycleway", "pedestrian")
PEDESTRIAN_CLASSES = ("footway", "pedestrian", "steps", "path")

# WHO Europe (2017): green spaces of at least 0.5 ha within 300 m — the size floor in m².
WHO_MIN_GREEN_M2 = 5_000

RAW_FILES = ("district", "segment", "infrastructure", "land_use", "land", "building")


def log(message: str) -> None:
    """Flush-print so progress shows through ``docker compose exec``."""
    print(message, flush=True)


def sql_list(values: tuple[str, ...]) -> str:
    """Render a tuple of strings as a SQL ``IN (...)`` body."""
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


def raw(name: str) -> str:
    """SQL fragment reading one raw parquet file."""
    return f"read_parquet('{(RAW_DIR / f'{name}.parquet').as_posix()}')"


def transform(expr: str) -> str:
    """4326 → 25831 with the axis-order flag that rule 9 requires."""
    return f"ST_Transform({expr}, '{DEG_CRS}', '{M_CRS}', always_xy := true)"


def sha256(path: Path) -> str:
    """Hex digest of a file, streamed."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_inputs() -> None:
    """Fail early with a clear message when the raw extract is missing."""
    missing = [n for n in RAW_FILES if not (RAW_DIR / f"{n}.parquet").exists()]
    if missing:
        raise SystemExit(
            f"missing raw files: {', '.join(missing)} — run `make load-data` (or `make extract`)"
        )


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Create every warehouse table from the raw extract."""
    con.execute("LOAD spatial")
    con.execute(SCHEMA.read_text(encoding="utf-8"))

    con.execute(
        f"""
        INSERT INTO district
        SELECT id, name, geometry, {transform("geometry")}, ST_Area({transform("geometry")})
        FROM {raw("district")}
        """
    )

    # Posted speed: prefer a rule without a `between` range (applies to the whole segment),
    # else the first rule. Only km/h is kept; the district has no other unit (Phase 0).
    con.execute(
        f"""
        INSERT INTO segments
        WITH src AS (
            SELECT s.id, s.name, s.class, s.subclass, s.geometry,
                   coalesce(
                       list_filter(s.speed_limits, r -> r.between IS NULL)[1],
                       s.speed_limits[1]
                   ) AS rule
            FROM {raw("segment")} s, {raw("district")} d
            WHERE s.subtype = 'road' AND ST_Intersects(s.geometry, d.geometry)
        )
        SELECT id, name, class, subclass,
               class NOT IN ({sql_list(NON_CARRIAGEWAY_CLASSES)}),
               class IN ({sql_list(PEDESTRIAN_CLASSES)}),
               CASE WHEN rule.max_speed.unit = 'km/h' THEN rule.max_speed.value END,
               rule.max_speed.value IS NOT NULL AND rule.max_speed.unit = 'km/h',
               ST_Length({transform("geometry")}),
               geometry, {transform("geometry")}
        FROM src
        """
    )

    con.execute(
        f"""
        INSERT INTO crossings
        SELECT i.id, i.geometry, {transform("i.geometry")}
        FROM {raw("infrastructure")} i, {raw("district")} d
        WHERE i.subtype = 'transportation' AND i.class = 'crossing'
          AND ST_GeometryType(i.geometry) = 'POINT'
          AND ST_Intersects(i.geometry, d.geometry)
        """
    )

    # Not clipped to the district on purpose: the nearest park to an edge building may be
    # outside it. The extract already limited these to the district bbox + 1.5 km.
    con.execute(
        f"""
        INSERT INTO green_spaces
        SELECT id, name, subtype, class,
               ST_Area({transform("geometry")}),
               ST_Area({transform("geometry")}) >= {WHO_MIN_GREEN_M2},
               geometry, {transform("geometry")}
        FROM {raw("land_use")}
        WHERE ST_GeometryType(geometry) IN ('POLYGON', 'MULTIPOLYGON')
        """
    )

    con.execute(
        f"""
        INSERT INTO buildings
        SELECT b.id, b.subtype, b.class,
               ST_Centroid(b.geometry), ST_Centroid({transform("b.geometry")})
        FROM {raw("building")} b, {raw("district")} d
        WHERE ST_Intersects(b.geometry, d.geometry)
        """
    )

    con.execute(
        f"""
        INSERT INTO trees
        SELECT t.id, t.geometry, {transform("t.geometry")}
        FROM {raw("land")} t, {raw("district")} d
        WHERE t.class = 'tree' AND ST_GeometryType(t.geometry) = 'POINT'
          AND ST_Intersects(t.geometry, d.geometry)
        """
    )

    rows = [
        ("overture_release", OVERTURE_RELEASE),
        ("built_at", datetime.now(UTC).isoformat(timespec="seconds")),
        ("crs_metric", M_CRS),
        *[(f"sha256:{n}.parquet", sha256(RAW_DIR / f"{n}.parquet")) for n in RAW_FILES],
    ]
    con.executemany("INSERT INTO meta VALUES (?, ?)", rows)


def row_counts(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int]]:
    """(table, rows) for every table, for the console summary and tests."""
    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    return [(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]) for t in tables]  # type: ignore[index]


def main() -> int:
    """Entry point for ``python -m pipeline.build``."""
    check_inputs()
    started = time.time()
    tmp = WAREHOUSE.with_suffix(".duckdb.tmp")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    build(con)
    counts = row_counts(con)
    con.close()
    tmp.replace(WAREHOUSE)  # atomic swap: readers never see a half-built file
    log(
        f"built {WAREHOUSE} ({WAREHOUSE.stat().st_size / 1e6:.1f} MB) "
        f"in {time.time() - started:.1f}s"
    )
    width = max(len(t) for t, _ in counts)
    for table, n in counts:
        log(f"  {table:<{width}}  {n:>9,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
