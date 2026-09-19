"""Phase 0 reconnaissance: what does the pinned Overture release carry for the district?

Produces evidence, not KPIs. Nothing here is reused by the warehouse; it exists so that the
KPI set is chosen against real counts rather than assumptions, and so the walkthrough can
cite them.

Steps:

1. Pull every theme/type we might use, bbox-filtered on read (predicate pushdown on the
   ``bbox`` struct), into ``data/raw/recon/<type>.parquet``. Idempotent: existing files are
   reused, so re-running is cheap and offline.
2. ``DESCRIBE`` each file and record the real schema.
3. Locate the district polygon in ``division_area`` and measure it in EPSG:25831.
4. Count features inside the district (``ST_Intersects`` against the polygon) with the
   categorical distributions a KPI would filter on.
5. Answer the questions that decide the KPI set (lamps, transit, pedestrian access,
   land-use coverage, plus the surprises: trees) as numbers.

Output: ``data/recon/recon.json`` (everything) and ``data/recon/recon.md`` (the same, as
tables). ``docs/recon.md`` is the committed, annotated copy.

Run inside the backend container::

    python -m pipeline.recon
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any

import duckdb

from pipeline.release import OVERTURE_RELEASE, OVERTURE_S3_REGION, overture_path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "recon"
OUT_DIR = DATA_DIR / "recon"
TIMINGS_FILE = RAW_DIR / "timings.json"

# Barcelona-wide bbox (lon/lat) used only for the download filter; the district polygon does
# the exact clipping afterwards.
BCN_BBOX = (2.05, 41.32, 2.24, 41.47)

DISTRICT_NAME = "l'Eixample"
FALLBACK_DISTRICTS = ("Gràcia", "Ciutat Vella")

# (theme, type) pairs worth looking at. `land` is included because Overture splits
# vegetation between land_use and land; a "green share" KPI needs to know which carries it.
TYPES: tuple[tuple[str, str], ...] = (
    ("divisions", "division_area"),
    ("transportation", "segment"),
    ("transportation", "connector"),
    ("base", "infrastructure"),
    ("base", "land_use"),
    ("base", "land"),
    ("base", "water"),
    ("buildings", "building"),
    ("places", "place"),
)

M_CRS = "EPSG:25831"
DEG_CRS = "EPSG:4326"

# Infrastructure classes that are a place where a person boards public transport.
# Parking, bicycle_parking etc. share the `transit` subtype and are deliberately excluded.
TRANSIT_STOP_CLASSES = (
    "bus_stop",
    "bus_station",
    "tram_stop",
    "subway_station",
    "railway_station",
    "platform",
    "stop_position",
)

TRANSIT_PATTERN = """
    subtype ILIKE '%transit%' OR subtype ILIKE '%rail%' OR subtype ILIKE '%transport%'
    OR class ILIKE '%bus%' OR class ILIKE '%tram%' OR class ILIKE '%subway%'
    OR class ILIKE '%metro%' OR class ILIKE '%station%' OR class ILIKE '%platform%'
    OR class ILIKE '%stop%' OR class ILIKE '%rail%'
"""

PLACE_TRANSIT_PATTERN = """
    categories.primary ILIKE '%bus%' OR categories.primary ILIKE '%tram%'
    OR categories.primary ILIKE '%metro%' OR categories.primary ILIKE '%subway%'
    OR categories.primary ILIKE '%train%' OR categories.primary ILIKE '%transit%'
    OR categories.primary ILIKE '%transport%' OR categories.primary ILIKE '%station%'
"""

# 1 km grid over the district in EPSG:25831, as a CTE. Cells are the cross product of the
# x and y kilometre indices spanned by the district bbox.
GRID_CTE = """
    cells AS (
        SELECT gx.cx, gy.cy,
               ST_MakeEnvelope(gx.cx * 1000, gy.cy * 1000,
                               gx.cx * 1000 + 1000, gy.cy * 1000 + 1000) AS cell
        FROM (SELECT unnest(range(CAST(floor(ST_XMin(geom_m) / 1000) AS INT),
                                  CAST(floor(ST_XMax(geom_m) / 1000) AS INT) + 1)) AS cx
              FROM district) gx
        CROSS JOIN
             (SELECT unnest(range(CAST(floor(ST_YMin(geom_m) / 1000) AS INT),
                                  CAST(floor(ST_YMax(geom_m) / 1000) AS INT) + 1)) AS cy
              FROM district) gy
    ),
    inside AS (
        SELECT c.cx, c.cy, ST_Intersection(c.cell, d.geom_m) AS cell_in_district,
               ST_Area(ST_Intersection(c.cell, d.geom_m)) / 1e6 AS km2_in_district
        FROM cells c, district d WHERE ST_Intersects(c.cell, d.geom_m)
    )
"""


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------


@dataclass
class Report:
    """Everything recon learns, in insertion order, serialisable to JSON and Markdown."""

    release: str
    sections: list[tuple[str, Any]] = field(default_factory=list)

    def add(self, title: str, value: Any) -> None:  # noqa: ANN401 - heterogeneous by design
        """Append one titled result (scalar, dict, or list of rows).

        A callable is evaluated here and a query failure is recorded as the section's
        value rather than aborting: a column that does not exist is a finding.
        """
        if callable(value):
            try:
                value = value()
            except duckdb.Error as exc:
                value = f"ERROR: {type(exc).__name__}: {str(exc).splitlines()[0]}"
        self.sections.append((title, value))
        log(f"  {title}: {summarise(value)}")

    def to_json(self) -> str:
        """Serialise the whole report."""
        payload = {"release": self.release, "sections": self.sections}
        return json.dumps(payload, indent=2, default=str)

    def to_markdown(self) -> str:
        """Render every section as a Markdown table or paragraph."""
        out = [f"# Recon output — Overture release `{self.release}`", ""]
        for title, value in self.sections:
            out.extend([f"## {title}", "", render(value), ""])
        return "\n".join(out)


def summarise(value: Any) -> str:  # noqa: ANN401
    """One-line preview for the console log."""
    if isinstance(value, list):
        return f"{len(value)} rows"
    text = json.dumps(value, default=str)
    return text if len(text) < 120 else text[:117] + "..."


def render(value: Any) -> str:  # noqa: ANN401
    """Render a section value as Markdown."""
    if isinstance(value, list) and value and isinstance(value[0], dict):
        cols = list(value[0].keys())
        head = "| " + " | ".join(cols) + " |"
        sep = "|" + "|".join("---" for _ in cols) + "|"
        body = ["| " + " | ".join(fmt(r.get(c)) for c in cols) + " |" for r in value]
        return "\n".join([head, sep, *body])
    if isinstance(value, dict):
        return "\n".join(f"- **{k}**: {fmt(v)}" for k, v in value.items())
    if isinstance(value, list) and not value:
        return "_(no rows)_"
    return fmt(value)


def fmt(value: Any) -> str:  # noqa: ANN401
    """Format a cell: floats to 2 dp, None as an em dash, pipes escaped."""
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def log(message: str) -> None:
    """Print with a flush so progress is visible through `docker compose exec`."""
    print(message, flush=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sql_str(value: str) -> str:
    """Quote a Python string as a SQL string literal (doubles embedded quotes)."""
    return "'" + value.replace("'", "''") + "'"


def rows(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    """Run a query and return rows as dicts (small result sets only)."""
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description or []]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def first(con: duckdb.DuckDBPyConnection, sql: str) -> dict[str, Any]:
    """First row as a dict."""
    return rows(con, sql)[0]


def scalar(con: duckdb.DuckDBPyConnection, sql: str) -> Any:  # noqa: ANN401
    """Run a query and return the first column of the first row."""
    row = con.execute(sql).fetchone()
    return None if row is None else row[0]


def connect() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with spatial + httpfs, anonymous S3 access to the Overture bucket."""
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_region = '{OVERTURE_S3_REGION}'")
    return con


def raw(type_: str) -> str:
    """SQL fragment reading one cached type."""
    return f"read_parquet('{(RAW_DIR / f'{type_}.parquet').as_posix()}')"


# ---------------------------------------------------------------------------
# Step 1 — download
# ---------------------------------------------------------------------------


def download(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Materialise each type for the Barcelona bbox. Skips files that already exist.

    Download durations are persisted next to the files so a cached re-run still reports
    what the first pull cost.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    xmin, ymin, xmax, ymax = BCN_BBOX
    timings: dict[str, float] = (
        json.loads(TIMINGS_FILE.read_text(encoding="utf-8")) if TIMINGS_FILE.exists() else {}
    )
    for theme, type_ in TYPES:
        target = RAW_DIR / f"{type_}.parquet"
        if target.exists():
            continue
        log(f"downloading {theme}/{type_} ...")
        started = time.time()
        tmp = target.with_suffix(".parquet.tmp")
        con.execute(
            f"""
            COPY (
                SELECT *
                FROM read_parquet('{overture_path(theme, type_)}', hive_partitioning = 1)
                WHERE bbox.xmin < {xmax} AND bbox.xmax > {xmin}
                  AND bbox.ymin < {ymax} AND bbox.ymax > {ymin}
            ) TO '{tmp.as_posix()}' (FORMAT PARQUET)
            """
        )
        tmp.replace(target)  # atomic: a failed download never masquerades as a cached file
        timings[type_] = round(time.time() - started, 1)
        TIMINGS_FILE.write_text(json.dumps(timings, indent=2), encoding="utf-8")
    report.add(
        "download timings (bbox-filtered, seconds, from the first pull)",
        [
            {
                "type": t,
                "seconds": timings.get(t),
                "mb": round((RAW_DIR / f"{t}.parquet").stat().st_size / 1e6, 1),
            }
            for _, t in TYPES
        ],
    )


# ---------------------------------------------------------------------------
# Step 2 — schemas
# ---------------------------------------------------------------------------


def schemas(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Record the real column layout of every downloaded type."""
    for _, type_ in TYPES:
        cols = rows(con, f"DESCRIBE SELECT * FROM {raw(type_)}")
        report.add(
            f"schema: {type_}",
            [{"column": c["column_name"], "type": c["column_type"]} for c in cols],
        )


# ---------------------------------------------------------------------------
# Step 3 — district
# ---------------------------------------------------------------------------


def district(con: duckdb.DuckDBPyConnection, report: Report) -> bool:
    """Find the district polygon; create the ``district`` table. Returns False if absent."""
    report.add(
        "division_area subtypes in the Barcelona bbox",
        partial(
            rows,
            con,
            f"SELECT subtype, count(*) AS n FROM {raw('division_area')} GROUP BY 1 ORDER BY 2 DESC",
        ),
    )
    names = ", ".join(sql_str(d) for d in (DISTRICT_NAME, *FALLBACK_DISTRICTS))
    candidates = rows(
        con,
        f"""
        SELECT names.primary AS name, subtype, class, ST_GeometryType(geometry) AS geometry_type,
               ST_Area(ST_Transform(geometry, '{DEG_CRS}', '{M_CRS}', always_xy := true)) / 1e6
                 AS area_km2,
               id
        FROM {raw("division_area")}
        WHERE names.primary IN ({names})
        ORDER BY name
        """,
    )
    report.add("district candidates (area in EPSG:25831)", candidates)

    chosen = [c for c in candidates if c["name"] == DISTRICT_NAME and c["subtype"] == "macrohood"]
    if not chosen:
        report.add("district", f"{DISTRICT_NAME} NOT FOUND as macrohood — fallback needed")
        return False
    con.execute(
        f"""
        CREATE TABLE district AS
        SELECT id, names.primary AS name, geometry AS geom,
               ST_Transform(geometry, '{DEG_CRS}', '{M_CRS}', always_xy := true) AS geom_m
        FROM {raw("division_area")}
        WHERE id = {sql_str(chosen[0]["id"])}
        """
    )
    report.add(
        "district",
        partial(
            first,
            con,
            """
            SELECT name, id, ST_GeometryType(geom) AS geometry_type,
                   ST_Area(geom_m) / 1e6 AS area_km2, ST_NPoints(geom) AS vertices,
                   ST_IsValid(geom) AS valid,
                   round(ST_XMin(geom), 5) AS xmin, round(ST_YMin(geom), 5) AS ymin,
                   round(ST_XMax(geom), 5) AS xmax, round(ST_YMax(geom), 5) AS ymax
            FROM district
            """,
        ),
    )
    return True


# ---------------------------------------------------------------------------
# Step 4 — counts inside the district
# ---------------------------------------------------------------------------


def clip_table(con: duckdb.DuckDBPyConnection, type_: str) -> None:
    """Create table ``<type>_d`` = rows intersecting the district, with ``geom_m`` added."""
    con.execute(
        f"""
        CREATE TABLE {type_}_d AS
        SELECT t.*, ST_Transform(t.geometry, '{DEG_CRS}', '{M_CRS}', always_xy := true) AS geom_m
        FROM {raw(type_)} t, district d
        WHERE ST_Intersects(t.geometry, d.geom)
        """
    )


def counts(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Row counts and categorical distributions for every type, inside the district."""
    types = [t for _, t in TYPES if t != "division_area"]
    for type_ in types:
        clip_table(con, type_)

    report.add(
        "row counts: Barcelona bbox vs inside district",
        lambda: [
            {
                "type": t,
                "rows_in_bbox": scalar(con, f"SELECT count(*) FROM {raw(t)}"),
                "rows_in_district": scalar(con, f"SELECT count(*) FROM {t}_d"),
            }
            for t in types
        ],
    )

    segments(con, report)
    connectors(con, report)
    infrastructure(con, report)
    surfaces(con, report)
    buildings(con, report)
    places(con, report)


def segments(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Segment distributions and the shape of the access columns."""
    add = report.add
    add(
        "segment: by subtype",
        partial(
            rows, con, "SELECT subtype, count(*) AS n FROM segment_d GROUP BY 1 ORDER BY 2 DESC"
        ),
    )
    add(
        "segment: by class (top 15) with clipped length km",
        partial(
            rows,
            con,
            """
            SELECT s.class, count(*) AS n,
                   sum(ST_Length(ST_Intersection(s.geom_m, d.geom_m))) / 1000 AS length_km_clipped
            FROM segment_d s, district d
            GROUP BY 1 ORDER BY 2 DESC LIMIT 15
            """,
        ),
    )
    add(
        "segment: class x subclass (top 15)",
        partial(
            rows,
            con,
            """
            SELECT class, subclass, count(*) AS n
            FROM segment_d GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15
            """,
        ),
    )
    add(
        "segment: nullness of the columns a walkability KPI would use",
        partial(
            first,
            con,
            """
            SELECT count(*) AS n,
                   count(subclass) AS has_subclass,
                   count(access_restrictions) AS has_access_restrictions,
                   count(road_surface) AS has_road_surface,
                   count(road_flags) AS has_road_flags,
                   count(speed_limits) AS has_speed_limits,
                   count(width_rules) AS has_width_rules,
                   count(level_rules) AS has_level_rules
            FROM segment_d
            """,
        ),
    )
    add(
        "segment: access_restrictions — access_type x mode x heading (unnested, top 15)",
        partial(
            rows,
            con,
            """
            WITH ar AS (
                SELECT unnest(access_restrictions) AS r FROM segment_d
                WHERE access_restrictions IS NOT NULL
            )
            SELECT r.access_type, list_aggregate(r.when.mode, 'string_agg', ',') AS modes,
                   r.when.heading AS heading, count(*) AS n
            FROM ar GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 15
            """,
        ),
    )
    add(
        "segment: road_flags values (unnested)",
        partial(
            rows,
            con,
            """
            WITH f AS (
                SELECT unnest(road_flags) AS fl FROM segment_d WHERE road_flags IS NOT NULL
            ),
            v AS (SELECT unnest(fl.values) AS flag FROM f)
            SELECT flag, count(*) AS n FROM v GROUP BY 1 ORDER BY 2 DESC
            """,
        ),
    )
    add(
        "segment: sample of three access_restrictions payloads (as JSON)",
        partial(
            rows,
            con,
            """
            SELECT class, subclass, to_json(access_restrictions) AS access_restrictions
            FROM segment_d WHERE access_restrictions IS NOT NULL
            ORDER BY random() LIMIT 3
            """,
        ),
    )


def road_safety(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Surprises from the cross-tab: speed limits and pedestrian crossings are well populated."""
    report.add(
        "Q6 speed limits: carriageway km by posted max speed (first speed_limits rule, km/h)",
        partial(
            rows,
            con,
            """
            WITH s AS (
                SELECT s.class, speed_limits[1].max_speed.value AS max_kmh,
                       speed_limits[1].max_speed.unit AS unit,
                       ST_Length(ST_Intersection(s.geom_m, d.geom_m)) / 1000 AS km
                FROM segment_d s, district d
                WHERE s.subtype = 'road'
                  AND s.class NOT IN ('footway', 'steps', 'path', 'cycleway', 'pedestrian')
            )
            SELECT CASE WHEN max_kmh IS NULL THEN 'no limit mapped'
                        WHEN max_kmh <= 20 THEN '<=20' WHEN max_kmh <= 30 THEN '21-30'
                        WHEN max_kmh <= 50 THEN '31-50' ELSE '>50' END AS band,
                   string_agg(DISTINCT unit, ',') AS unit,
                   count(*) AS segments, sum(km) AS km
            FROM s GROUP BY 1 ORDER BY 4 DESC
            """,
        ),
    )
    report.add(
        "Q6 speed limits: share of carriageway km with a mapped limit, by class",
        partial(
            rows,
            con,
            """
            SELECT s.class, count(*) AS n, count(speed_limits) AS with_limit,
                   round(100.0 * count(speed_limits) / count(*), 1) AS pct_with_limit
            FROM segment_d s
            WHERE s.subtype = 'road'
              AND s.class NOT IN ('footway', 'steps', 'path', 'cycleway', 'pedestrian')
            GROUP BY 1 ORDER BY 2 DESC
            """,
        ),
    )
    report.add(
        "Q7 crossings and signals: infrastructure points per km of carriageway",
        partial(
            first,
            con,
            """
            WITH road AS (
                SELECT sum(ST_Length(ST_Intersection(s.geom_m, d.geom_m))) / 1000 AS km
                FROM segment_d s, district d
                WHERE s.subtype = 'road'
                  AND s.class NOT IN ('footway', 'steps', 'path', 'cycleway', 'pedestrian')
            )
            SELECT (SELECT km FROM road) AS carriageway_km,
                   count(*) FILTER (WHERE class = 'crossing') AS crossings,
                   count(*) FILTER (WHERE class = 'crossing') / (SELECT km FROM road)
                     AS crossings_per_km,
                   count(*) FILTER (WHERE class = 'traffic_signals') AS traffic_signals,
                   count(*) FILTER (WHERE class = 'traffic_signals') / (SELECT km FROM road)
                     AS signals_per_km,
                   count(*) FILTER (WHERE class = 'crossing'
                                    AND ST_GeometryType(geometry) = 'POINT') AS crossings_as_points
            FROM infrastructure_d WHERE subtype = 'transportation'
            """,
        ),
    )


def connectors(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Connector degree: how many district segments reference each connector."""
    report.add(
        "connector: degree distribution (segments in district referencing the connector)",
        partial(
            rows,
            con,
            """
            WITH refs AS (
                SELECT unnest(connectors).connector_id AS connector_id FROM segment_d
            ),
            degree AS (
                SELECT c.id, count(r.connector_id) AS degree
                FROM connector_d c LEFT JOIN refs r ON r.connector_id = c.id
                GROUP BY c.id
            )
            SELECT CASE WHEN degree >= 4 THEN '4+' ELSE CAST(degree AS VARCHAR) END AS degree,
                   count(*) AS n
            FROM degree GROUP BY 1 ORDER BY 1
            """,
        ),
    )


def infrastructure(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Full subtype x class cross-tab, lamps under every subtype, transit-looking rows."""
    add = report.add
    add(
        "infrastructure: subtype x class (full cross-tab)",
        partial(
            rows,
            con,
            """
            SELECT subtype, class, count(*) AS n
            FROM infrastructure_d GROUP BY 1, 2 ORDER BY 1, 3 DESC
            """,
        ),
    )
    add(
        "infrastructure: geometry types",
        partial(
            rows,
            con,
            """
            SELECT ST_GeometryType(geometry) AS gt, count(*) AS n
            FROM infrastructure_d GROUP BY 1 ORDER BY 2 DESC
            """,
        ),
    )
    add(
        "infrastructure: street lamps as PLAN.md named them "
        "(subtype='utility', class='street_lamp')",
        partial(
            scalar,
            con,
            """
            SELECT count(*) FROM infrastructure_d
            WHERE subtype = 'utility' AND class = 'street_lamp'
            """,
        ),
    )
    add(
        "infrastructure: street lamps under any subtype (class='street_lamp')",
        partial(
            rows,
            con,
            """
            SELECT subtype, ST_GeometryType(geometry) AS gt, count(*) AS n
            FROM infrastructure_d WHERE class = 'street_lamp' GROUP BY 1, 2 ORDER BY 3 DESC
            """,
        ),
    )
    add(
        "infrastructure: anything transit-looking (subtype/class ILIKE bus|tram|subway|metro|"
        "station|platform|stop|rail)",
        partial(
            rows,
            con,
            f"""
            SELECT subtype, class, count(*) AS n FROM infrastructure_d
            WHERE {TRANSIT_PATTERN}
            GROUP BY 1, 2 ORDER BY 3 DESC
            """,
        ),
    )


def surfaces(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """land_use, land and water: counts and clipped areas by class."""
    for t in ("land_use", "land"):
        report.add(
            f"{t}: by subtype x class with clipped area km2",
            partial(
                rows,
                con,
                f"""
                SELECT t.subtype, t.class, ST_GeometryType(t.geometry) AS gt, count(*) AS n,
                       sum(CASE WHEN ST_GeometryType(t.geometry) IN ('POLYGON', 'MULTIPOLYGON')
                                THEN ST_Area(ST_Intersection(t.geom_m, d.geom_m)) ELSE 0 END)
                         / 1e6 AS area_km2_clipped
                FROM {t}_d t, district d
                GROUP BY 1, 2, 3 ORDER BY 5 DESC, 4 DESC
                """,
            ),
        )
    report.add(
        "water: by subtype x class with clipped area km2",
        partial(
            rows,
            con,
            """
            SELECT t.subtype, t.class, ST_GeometryType(t.geometry) AS gt, count(*) AS n,
                   sum(CASE WHEN ST_GeometryType(t.geometry) IN ('POLYGON', 'MULTIPOLYGON')
                            THEN ST_Area(ST_Intersection(t.geom_m, d.geom_m)) ELSE 0 END) / 1e6
                     AS area_km2_clipped
            FROM water_d t, district d
            GROUP BY 1, 2, 3 ORDER BY 4 DESC
            """,
        ),
    )


def buildings(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Building totals, attribute coverage and subtype distribution."""
    report.add(
        "building: totals and attribute coverage",
        partial(
            first,
            con,
            """
            SELECT count(*) AS n,
                   count(height) AS has_height,
                   count(num_floors) AS has_num_floors,
                   count(class) AS has_class,
                   count(subtype) AS has_subtype,
                   sum(ST_Area(ST_Intersection(b.geom_m, d.geom_m))) / 1e6
                     AS footprint_km2_clipped
            FROM building_d b, district d
            """,
        ),
    )
    report.add(
        "building: by subtype (top 15)",
        partial(
            rows,
            con,
            "SELECT subtype, count(*) AS n FROM building_d GROUP BY 1 ORDER BY 2 DESC LIMIT 15",
        ),
    )


def places(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Place category distribution, confidence and transit-looking categories."""
    add = report.add
    add(
        "place: top 20 primary categories",
        partial(
            rows,
            con,
            """
            SELECT categories.primary AS category, count(*) AS n
            FROM place_d GROUP BY 1 ORDER BY 2 DESC LIMIT 20
            """,
        ),
    )
    add(
        "place: confidence distribution",
        partial(
            rows,
            con,
            """
            SELECT CASE WHEN confidence >= 0.9 THEN '>=0.9' WHEN confidence >= 0.7 THEN '0.7-0.9'
                        WHEN confidence >= 0.5 THEN '0.5-0.7' ELSE '<0.5' END AS confidence_band,
                   count(*) AS n
            FROM place_d GROUP BY 1 ORDER BY 1
            """,
        ),
    )
    add(
        "place: transit-looking categories (category ILIKE bus|tram|metro|subway|train|transit|"
        "transport|station)",
        partial(
            rows,
            con,
            f"""
            SELECT categories.primary AS category, count(*) AS n FROM place_d
            WHERE {PLACE_TRANSIT_PATTERN}
            GROUP BY 1 ORDER BY 2 DESC
            """,
        ),
    )


# ---------------------------------------------------------------------------
# Step 5 — the questions that decide the KPI set
# ---------------------------------------------------------------------------


def questions(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Lamps, transit, pedestrian access, land-use coverage and trees, as numbers."""
    lamps(con, report)
    transit(con, report)
    pedestrian(con, report)
    coverage(con, report)
    trees(con, report)
    road_safety(con, report)


def lamps(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Q1: how many lamps, how far apart, how evenly spread."""
    con.execute(
        """
        CREATE TABLE lamps AS
        SELECT id, geom_m FROM infrastructure_d
        WHERE class = 'street_lamp' AND ST_GeometryType(geometry) = 'POINT'
        """
    )
    report.add(
        "Q1 lamps: count, nearest-neighbour distance (m), lamps per km of road",
        partial(
            first,
            con,
            """
            WITH nn AS (
                SELECT a.id,
                       (SELECT min(ST_Distance(a.geom_m, b.geom_m)) FROM lamps b
                        WHERE b.id <> a.id AND ST_DWithin(a.geom_m, b.geom_m, 500)) AS d
                FROM lamps a
            ),
            road AS (
                SELECT sum(ST_Length(ST_Intersection(s.geom_m, d.geom_m))) / 1000 AS km
                FROM segment_d s, district d
                WHERE s.subtype = 'road' AND s.class NOT IN ('footway', 'steps', 'path', 'cycleway')
            )
            SELECT count(*) AS lamps,
                   count(d) AS with_neighbour_within_500m,
                   quantile_cont(d, 0.5) AS median_nn_m,
                   quantile_cont(d, 0.25) AS p25_nn_m,
                   quantile_cont(d, 0.75) AS p75_nn_m,
                   quantile_cont(d, 0.9) AS p90_nn_m,
                   (SELECT km FROM road) AS carriageway_km_excl_footway_cycleway,
                   count(*) / (SELECT km FROM road) AS lamps_per_carriageway_km,
                   1000 * (SELECT km FROM road) / count(*) AS mean_m_of_carriageway_per_lamp
            FROM nn
            """,
        ),
    )
    report.add(
        "Q1 lamps: per 1 km grid cell summary (EPSG:25831 cells; 'mostly inside' = >0.9 km2 in "
        "district)",
        partial(
            first,
            con,
            f"""
            WITH {GRID_CTE},
            per_cell AS (
                SELECT i.cx, i.cy, i.km2_in_district,
                       (SELECT count(*) FROM lamps l WHERE ST_Within(l.geom_m, i.cell_in_district))
                         AS lamps
                FROM inside i
            )
            SELECT count(*) AS cells,
                   sum(CASE WHEN km2_in_district > 0.9 THEN 1 ELSE 0 END) AS cells_mostly_inside,
                   min(lamps) AS min_lamps,
                   quantile_cont(lamps, 0.5) AS median_lamps,
                   max(lamps) AS max_lamps,
                   sum(CASE WHEN lamps = 0 THEN 1 ELSE 0 END) AS cells_with_zero_lamps,
                   min(CASE WHEN km2_in_district > 0.9 THEN lamps END) AS min_mostly_inside,
                   quantile_cont(CASE WHEN km2_in_district > 0.9 THEN lamps END, 0.5)
                     AS median_mostly_inside,
                   max(CASE WHEN km2_in_district > 0.9 THEN lamps END) AS max_mostly_inside
            FROM per_cell
            """,
        ),
    )
    report.add(
        "Q1 lamps: per-cell detail (cx, cy are EPSG:25831 km indices)",
        partial(
            rows,
            con,
            f"""
            WITH {GRID_CTE}
            SELECT i.cx, i.cy, i.km2_in_district,
                   (SELECT count(*) FROM lamps l WHERE ST_Within(l.geom_m, i.cell_in_district))
                     AS lamps,
                   (SELECT sum(ST_Length(ST_Intersection(s.geom_m, i.cell_in_district))) / 1000
                    FROM segment_d s
                    WHERE s.subtype = 'road' AND ST_Intersects(s.geom_m, i.cell_in_district))
                     AS road_km_all_classes
            FROM inside i
            ORDER BY cx, cy
            """,
        ),
    )


def transit(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Q2: stops exist? how many? and how far is a building from the nearest one."""
    classes = ", ".join(sql_str(c) for c in TRANSIT_STOP_CLASSES)
    report.add(
        "Q2 transit: totals",
        lambda: {
            "infrastructure rows matching the loose transit pattern": scalar(
                con, f"SELECT count(*) FROM infrastructure_d WHERE {TRANSIT_PATTERN}"
            ),
            "infrastructure boarding places (subtype='transit', class in stop classes)": scalar(
                con,
                f"""
                SELECT count(*) FROM infrastructure_d
                WHERE subtype = 'transit' AND class IN ({classes})
                """,
            ),
            "place rows matching the loose transit pattern": scalar(
                con, f"SELECT count(*) FROM place_d WHERE {PLACE_TRANSIT_PATTERN}"
            ),
            "segment rows with subtype='rail'": scalar(
                con, "SELECT count(*) FROM segment_d WHERE subtype = 'rail'"
            ),
        },
    )
    report.add(
        "Q2 transit: boarding places by class and geometry type",
        partial(
            rows,
            con,
            f"""
            SELECT class, ST_GeometryType(geometry) AS gt, count(*) AS n
            FROM infrastructure_d
            WHERE subtype = 'transit' AND class IN ({classes})
            GROUP BY 1, 2 ORDER BY 3 DESC
            """,
        ),
    )
    report.add(
        "Q2 transit: building-centroid distance (m) to nearest bus_stop / subway_station "
        "(feasibility of a distance KPI and where its thresholds would bite)",
        partial(
            first,
            con,
            """
            WITH stops AS (
                SELECT class, ST_Centroid(geom_m) AS g FROM infrastructure_d
                WHERE subtype = 'transit' AND class IN ('bus_stop', 'subway_station')
            ),
            b AS (SELECT ST_Centroid(geom_m) AS g FROM building_d),
            d AS (
                SELECT (SELECT min(ST_Distance(b.g, s.g)) FROM stops s) AS any_stop,
                       (SELECT min(ST_Distance(b.g, s.g)) FROM stops s WHERE s.class = 'bus_stop')
                         AS bus,
                       (SELECT min(ST_Distance(b.g, s.g)) FROM stops s
                        WHERE s.class = 'subway_station') AS subway
                FROM b
            )
            SELECT count(*) AS buildings,
                   quantile_cont(any_stop, 0.5) AS p50_any_stop_m,
                   quantile_cont(any_stop, 0.9) AS p90_any_stop_m,
                   quantile_cont(bus, 0.5) AS p50_bus_m,
                   quantile_cont(subway, 0.5) AS p50_subway_m,
                   100.0 * sum(CASE WHEN any_stop <= 300 THEN 1 ELSE 0 END) / count(*)
                     AS pct_within_300m,
                   100.0 * sum(CASE WHEN any_stop <= 500 THEN 1 ELSE 0 END) / count(*)
                     AS pct_within_500m
            FROM d
            """,
        ),
    )


def pedestrian(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Q3: can a walkable / non-walkable split be derived from the columns that exist."""
    # A restriction with no `when` condition at all applies to every mode; one with only a
    # heading is a one-way rule, not an access rule. A struct with all-null fields is not
    # NULL in DuckDB, hence the explicit field checks.
    unconditional = """
        r.when IS NULL OR (
            r.when.mode IS NULL AND r.when.heading IS NULL AND r.when.during IS NULL
            AND r.when.using IS NULL AND r.when.recognized IS NULL AND r.when.vehicle IS NULL
        )
    """
    report.add(
        "Q3 pedestrian: road segments by class — clipped km, and segments with an access rule "
        "that denies foot explicitly, denies unconditionally, or is only a one-way rule",
        partial(
            rows,
            con,
            f"""
            SELECT s.class, count(*) AS n,
                   sum(ST_Length(ST_Intersection(s.geom_m, d.geom_m))) / 1000 AS length_km,
                   sum(CASE WHEN len(list_filter(coalesce(s.access_restrictions, []),
                            r -> r.access_type = 'denied'
                                 AND list_contains(coalesce(r.when.mode, []), 'foot'))) > 0
                            THEN 1 ELSE 0 END) AS n_foot_denied,
                   sum(CASE WHEN len(list_filter(coalesce(s.access_restrictions, []),
                            r -> r.access_type = 'denied' AND ({unconditional}))) > 0
                            THEN 1 ELSE 0 END) AS n_denied_unconditionally,
                   sum(CASE WHEN len(list_filter(coalesce(s.access_restrictions, []),
                            r -> r.access_type = 'denied' AND r.when.heading IS NOT NULL
                                 AND r.when.mode IS NULL)) > 0
                            THEN 1 ELSE 0 END) AS n_one_way_only
            FROM segment_d s, district d
            WHERE s.subtype = 'road'
            GROUP BY 1 ORDER BY 3 DESC
            """,
        ),
    )


def coverage(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Q4: what share of the district has any land_use polygon at all."""

    def union_km2(table: str, where: str = "TRUE") -> float | None:
        value = scalar(
            con,
            f"""
            SELECT ST_Area(ST_Intersection(ST_Union_Agg(t.geom_m), d.geom_m)) / 1e6
            FROM {table} t, district d
            WHERE ST_GeometryType(t.geometry) IN ('POLYGON', 'MULTIPOLYGON') AND ({where})
            GROUP BY d.geom_m
            """,
        )
        return None if value is None else float(value)

    def pct(part: float | None, whole: float) -> float | None:
        return None if part is None else 100 * part / whole

    def build() -> dict[str, Any]:
        district_km2 = float(scalar(con, "SELECT ST_Area(geom_m) / 1e6 FROM district"))
        land_use = union_km2("land_use_d")
        green = union_km2(
            "land_use_d",
            "t.subtype IN ('park', 'horticulture', 'managed', 'recreation', 'agriculture')",
        )
        land_veg = union_km2("land_d", "t.subtype IN ('forest', 'shrub', 'grass', 'tree')")
        water = union_km2("water_d")
        footprint = union_km2("building_d")
        return {
            "district_km2": district_km2,
            "land_use_union_km2": land_use,
            "land_use_coverage_pct": pct(land_use, district_km2),
            "green_land_use_union_km2 (park/horticulture/managed/recreation/agriculture)": green,
            "green_land_use_pct": pct(green, district_km2),
            "land_vegetation_polygons_km2 (forest/shrub/grass/tree)": land_veg,
            "water_union_km2": water,
            "water_pct": pct(water, district_km2),
            "building_footprint_union_km2": footprint,
            "building_footprint_pct": pct(footprint, district_km2),
        }

    report.add("Q4 land-use coverage and the shares a green/water KPI would produce", build)


def trees(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    """Surprise finding: individual trees are mapped as points in base/land."""
    report.add(
        "Q5 trees (base/land, subtype='tree'): count, per km of carriageway, per 1 km cell",
        partial(
            first,
            con,
            f"""
            WITH {GRID_CTE},
            t AS (SELECT geom_m FROM land_d WHERE class = 'tree'),
            road AS (
                SELECT sum(ST_Length(ST_Intersection(s.geom_m, d.geom_m))) / 1000 AS km
                FROM segment_d s, district d
                WHERE s.subtype = 'road' AND s.class NOT IN ('footway', 'steps', 'path', 'cycleway')
            ),
            per_cell AS (
                SELECT i.km2_in_district,
                       (SELECT count(*) FROM t WHERE ST_Within(t.geom_m, i.cell_in_district)) AS n
                FROM inside i WHERE i.km2_in_district > 0.9
            )
            SELECT (SELECT count(*) FROM t) AS trees,
                   (SELECT count(*) FROM t) / (SELECT km FROM road) AS trees_per_carriageway_km,
                   (SELECT count(*) FROM land_d WHERE class = 'tree_row') AS tree_rows,
                   min(n) AS min_per_full_cell, quantile_cont(n, 0.5) AS median_per_full_cell,
                   max(n) AS max_per_full_cell
            FROM per_cell
            """,
        ),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Run every step and write the report. Returns a process exit code."""
    started = time.time()
    report = Report(release=OVERTURE_RELEASE)
    con = connect()
    log(f"release {OVERTURE_RELEASE}; duckdb {duckdb.__version__}")

    download(con, report)
    schemas(con, report)
    if district(con, report):
        counts(con, report)
        questions(con, report)
    else:
        log("district not found; counts skipped — see report")

    report.add("total recon seconds", round(time.time() - started, 1))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "recon.json").write_text(report.to_json(), encoding="utf-8")
    (OUT_DIR / "recon.md").write_text(report.to_markdown(), encoding="utf-8")
    log(f"wrote {OUT_DIR / 'recon.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
