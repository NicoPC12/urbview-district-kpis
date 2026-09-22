"""Derive band boundaries from the district's own distribution — show the method.

Every band boundary that has no citation is *derived*, not picked: the district is gridded
into 250 m cells (EPSG:25831, clipped to the district), each KPI is computed per cell with
the very SQL the API runs, cells with too little denominator are dropped, and the cutoffs are
the 33rd and 67th percentiles of the per-cell values rounded to two significant figures. The
same grid answers a data-quality question the pedestrian KPI depends on: is sidewalk mapping
uniform across the district, or patchy (in which case the KPI would measure OSM coverage)?

Re-runnable: ``make derive-bands`` runs it in the backend container and writes the Markdown
report to ``docs/derived_bands.md``. The numbers go into a data migration by hand — a
migration must stay frozen, so it never imports this module.
"""

from __future__ import annotations

import math
import os
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb

from apps.kpis.registry import SPEC_BY_KEY
from warehouse import area as warehouse_area
from warehouse.connection import connect, transform_to_deg
from warehouse.kpi import run_kpi

WAREHOUSE = Path(os.environ.get("WAREHOUSE_PATH", "data/warehouse.duckdb"))

CELL_M = 250.0
# Chosen: a cell with less than 500 m of carriageway is a park edge or a district corner
# where one segment decides the value; the report says how many cells this drops.
MIN_CARRIAGEWAY_KM = 0.5
PERCENTILES = (33, 67)

# KPI key -> the context key that carries its denominator in km.
DENOMINATOR = {
    "low_speed_street_share": "mapped_km",
    "crossing_density": "carriageway_km",
    "pedestrian_network_share": "network_km",
    "street_tree_density": "carriageway_km",
}


@dataclass(frozen=True)
class Cell:
    """One grid cell: index, EPSG:4326 WKT of cell ∩ district, area in km²."""

    ix: int
    iy: int
    wkt: str
    km2: float


def round_sig(value: float, digits: int = 2) -> float:
    """Round to ``digits`` significant figures (37.2 -> 37, 8.41 -> 8.4, 0.512 -> 0.51)."""
    if value == 0:
        return 0.0
    return round(value, digits - 1 - math.floor(math.log10(abs(value))))


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile, same definition as DuckDB's quantile_cont."""
    xs = sorted(values)
    pos = (len(xs) - 1) * pct / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def grid(con: duckdb.DuckDBPyConnection) -> list[Cell]:
    """250 m cells over the district bbox in EPSG:25831, each clipped to the district."""
    rows = con.execute(
        f"""
        WITH d AS (SELECT geom_m FROM district),
             b AS (SELECT floor(ST_XMin(geom_m) / {CELL_M}) AS x0,
                          floor(ST_YMin(geom_m) / {CELL_M}) AS y0,
                          ceil(ST_XMax(geom_m) / {CELL_M}) AS x1,
                          ceil(ST_YMax(geom_m) / {CELL_M}) AS y1
                   FROM d),
             ix AS (SELECT unnest(range(x0::INT, x1::INT)) AS ix FROM b),
             iy AS (SELECT unnest(range(y0::INT, y1::INT)) AS iy FROM b),
             cells AS (
                 SELECT ix, iy,
                        ST_Intersection(
                            ST_MakeEnvelope(ix * {CELL_M}, iy * {CELL_M},
                                            (ix + 1) * {CELL_M}, (iy + 1) * {CELL_M}),
                            d.geom_m) AS geom_m
                 FROM ix, iy, d
             )
        SELECT ix, iy, ST_AsText({transform_to_deg("geom_m")}), ST_Area(geom_m) / 1e6
        FROM cells
        WHERE NOT ST_IsEmpty(geom_m) AND ST_Area(geom_m) > 0
        ORDER BY iy, ix
        """
    ).fetchall()
    return [Cell(int(r[0]), int(r[1]), str(r[2]), float(r[3])) for r in rows]


def per_cell_values(
    con: duckdb.DuckDBPyConnection, cells: list[Cell]
) -> dict[str, list[tuple[Cell, float | None, float]]]:
    """(cell, value, denominator km) per KPI, using the production SQL on each cell."""
    out: dict[str, list[tuple[Cell, float | None, float]]] = {k: [] for k in DENOMINATOR}
    for cell in cells:
        warehouse_area.register_area(con, cell.wkt)
        for key, denominator_key in DENOMINATOR.items():
            row = run_kpi(con, SPEC_BY_KEY[key].sql)
            denominator = next((c.value for c in row.context if c.key == denominator_key), None)
            out[key].append((cell, row.value, denominator or 0.0))
    return out


def sidewalk_ratio(con: duckdb.DuckDBPyConnection, cells: list[Cell]) -> list[float]:
    """Per cell: mapped sidewalk km / carriageway km (cells under the minimum skipped)."""
    ratios: list[float] = []
    for cell in cells:
        warehouse_area.register_area(con, cell.wkt)
        row = con.execute(
            """
            WITH clipped AS (
                SELECT subclass, is_carriageway,
                       ST_Length(ST_Intersection(geom_m, area_m())) AS len_m
                FROM segments WHERE ST_Intersects(geom_m, area_m())
            )
            SELECT sum(len_m) FILTER (WHERE subclass = 'sidewalk') / 1000,
                   sum(len_m) FILTER (WHERE is_carriageway) / 1000
            FROM clipped
            """
        ).fetchone()
        assert row is not None  # noqa: S101
        sidewalk_km, carriageway_km = float(row[0] or 0), float(row[1] or 0)
        if carriageway_km >= MIN_CARRIAGEWAY_KM:
            ratios.append(sidewalk_km / carriageway_km)
    return ratios


def main() -> int:
    """Print the Markdown report (stdout)."""
    con = connect(WAREHOUSE)
    release = con.execute("SELECT value FROM meta WHERE key = 'overture_release'").fetchone()
    cells = grid(con)
    values = per_cell_values(con, cells)
    ratios = sidewalk_ratio(con, cells)

    print(f"# Derived bands — {len(cells)} cells of {CELL_M:.0f} m over the district\n")
    print(
        f"Overture {release[0] if release else '?'}. {CELL_M:.0f} m grid in EPSG:25831 clipped "
        f"to the district; each KPI computed per cell with the production SQL; cells with less "
        f"than {MIN_CARRIAGEWAY_KM} km of denominator dropped (chosen); cutoffs = "
        f"P{PERCENTILES[0]} "
        f"and P{PERCENTILES[1]} of the per-cell values, rounded to two significant figures. "
        f"Regenerate with `make derive-bands`.\n"
    )
    print("| KPI | cells kept | dropped (< 0.5 km) | min | P33 | median | P67 | max | cutoffs |")
    print("|---|---|---|---|---|---|---|---|---|")
    for key, rows in values.items():
        kept = [v for _, v, d in rows if v is not None and d >= MIN_CARRIAGEWAY_KM]
        dropped = len(rows) - len(kept)
        p33, p67 = (percentile(kept, p) for p in PERCENTILES)
        cutoffs = [round_sig(p33), round_sig(p67)]
        print(
            f"| `{key}` | {len(kept)} | {dropped} | {min(kept):.1f} | {p33:.1f} | "
            f"{statistics.median(kept):.1f} | {p67:.1f} | {max(kept):.1f} | "
            f"**{cutoffs[0]:g} / {cutoffs[1]:g}** |"
        )

    print("\n# Sidewalk mapping per cell — sidewalk km / carriageway km\n")
    qs = {p: percentile(ratios, p) for p in (10, 25, 50, 75, 90)}
    print(
        f"cells: {len(ratios)} · min {min(ratios):.2f} · P10 {qs[10]:.2f} · P25 {qs[25]:.2f} · "
        f"median {qs[50]:.2f} · P75 {qs[75]:.2f} · P90 {qs[90]:.2f} · max {max(ratios):.2f} · "
        f"cells with ratio < 0.5: {sum(r < 0.5 for r in ratios)} · "
        f"cells with ratio > 1.5: {sum(r > 1.5 for r in ratios)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
