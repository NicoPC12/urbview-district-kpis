# UrbView — district KPI dashboard

A single page: a map of Barcelona's Eixample beside a KPI dashboard, where drawing a polygon
recomputes every KPI for that polygon alone. Data source: Overture Maps release
`2026-08-19.0`, and nothing else.

**Walkthrough deck: [`walkthrough/walkthrough.pdf`](walkthrough/walkthrough.pdf)** (12 slides).

## Setup

```bash
docker compose up --build   # 1. app on http://localhost:5173, API on http://localhost:8000
make load-data              # 2. fetch the prepared Overture extract, build data/warehouse.duckdb
```

Prerequisites: Docker Desktop and GNU `make` (Windows: `winget install GnuWin32.Make`, run
from Git Bash). Python and Node run inside the containers.

Measured timings: cold `docker compose up --build` on a machine with no cached images
**2 min 50 s**; with the base images already pulled but every layer rebuilt
(`--no-cache`) **1 min 39 s**, plus **48 s** from `up` to both services answering.
`make load-data` is **8–9 s** from the release asset, or **~11 min** if it falls back to
pulling from Overture's S3 bucket. Re-verified end to end on 2026-09-25 from a fresh clone
with empty volumes.

What you should see: before step 2 the page says *Warehouse not loaded — run `make
load-data`*; after it, without restarting anything, the map shows the district outline with
its streets coloured by posted speed and the dashboard reads **50.7 %** on the first card.
Press **Draw area**, click a few points, click the first point to close: every card
recomputes for the polygon (under a second), the district stays underneath as dimmed context, and
**Clear drawing** brings the district back. Click a card to switch the map layer, a chart
bar or legend chip to emphasise that category, a street or point to see its contribution.

| URL | What |
|---|---|
| `http://localhost:5173` | The app (desktop only) |
| `POST http://localhost:8000/api/v1/kpis` | Every KPI for `{"district": "eixample"}`, `{"bbox": [...]}` or `{"polygon": <GeoJSON>}` |
| `http://localhost:8000/api/v1/districts` | District outline and bounds |
| `http://localhost:8000/api/schema/` · `/api/docs/` | OpenAPI schema (the source of the generated frontend types) · Swagger UI |
| `http://localhost:8000/admin/` | KPI labels, bands and citations as editable rows — login `admin` / `admin` |

```bash
curl -s --compressed localhost:8000/api/v1/kpis -H 'Content-Type: application/json' \
  -d '{"polygon":{"type":"Polygon","coordinates":[[[2.160,41.390],[2.170,41.390],[2.170,41.397],[2.160,41.397],[2.160,41.390]]]}}'
```

Other commands (`make help` lists them all): `make test`, `make lint`, `make types`
(regenerate `frontend/src/api/schema.gen.ts`), `make extract` (real Overture S3 pull,
~10 min), `make warehouse` (rebuild from `data/raw/`), `make down`.

**If 5173 or 8000 are already taken**, set `FRONTEND_PORT` / `BACKEND_PORT` (in the
environment or a repo-root `.env`) and re-run — for example
`FRONTEND_PORT=5174 BACKEND_PORT=8001 docker compose up --build`, then open the app on the
port you chose. Postgres is not published to the host at all, so a database already running
on 5432 cannot collide with this stack; reach the container's with
`docker compose exec db psql -U urbview urbview`.

## What I built

- **Pipeline** — [`backend/pipeline/`](backend/pipeline/): pinned Overture release, bbox
  pushdown extract of six themes (6.8 MB of Parquet), a DuckDB warehouse with EPSG:4326 and
  EPSG:25831 geometry side by side and an R-tree per table, and a checksummed prepared-extract
  download with automatic S3 fallback.
- **Five KPIs** — one SQL file each in [`backend/warehouse/queries/`](backend/warehouse/queries/);
  clipping, joins, lengths and distances all in DuckDB, Python never iterates a geometry.
  Definitions, bands and citations in [`NOTES.md`](NOTES.md) and, at runtime, in Postgres.
  Two thresholds are cited (30 km/h, WHO 300 m / 0.5 ha); the rest are *derived* from the
  district's own 250 m-cell distribution by a committed, re-runnable script
  (`make derive-bands`), never picked by hand.
- **API** — `POST /api/v1/kpis` with RFC 7807 errors, GZip, a self-invalidating cache, KPI
  metadata in Postgres behind the Django admin, a system check that refuses to start if code
  and database disagree, and one read-only DuckDB connection per process with a cursor per
  request.
- **Page** — MapLibre + terra-draw beside a React dashboard, one Zustand store holding
  selection only; numbers live once, in TanStack Query keyed by the area. Both interaction
  directions, all four states, types generated from the OpenAPI schema.

## Deviations from the brief

- **REST + OpenAPI codegen, not GraphQL.** The rubric wants generated client types;
  `openapi-typescript` gives that for a fraction of the setup inside a 10-hour budget.
- **The extract is published in a separate public data-only repository**
  ([`NicoPC12/urbview-data`](https://github.com/NicoPC12/urbview-data)) as a release asset.
  The brief says commit the script, not the data, *and* be running in fifteen minutes; the
  asset satisfies both, the S3 pull stays one command away, and this repository stays private.
- **Dev defaults in `docker-compose.yml` and `dev.py`** (Postgres password, `django-insecure-`
  key, `admin`/`admin`). They guard a local container nobody can reach; a required
  `cp .env.example .env` would make the two-command setup three. `prod.py` takes no defaults.
- **An OSM-derived basemap under the data.** OpenFreeMap tiles are cartographic context only;
  no KPI reads them, nothing joins to them, every number comes from Overture (NOTES "Basemap").
- **Desktop only.** A fixed map/dashboard split; a phone layout was not attempted rather than
  half-done.

## What I cut and why

- **Lamps, transit, land-use mix, green share, junction density** as KPIs — each for one
  number found in reconnaissance (NOTES "Rejected KPIs"): lamps measure mapping effort,
  transit has no spatial variance, land use covers 30 % of the district.
- **Mobile layout** — see above.
- **Vector tiles.** The district response is 5.1 MB raw / 0.98 MB gzipped; fine for one district,
  the wrong shape at 10×. Static geometry as tiles plus per-request ids is the walkthrough's
  answer, not this week's build.
- **Async jobs.** Every request finishes under 3 s cold and 0.5 s cached; a queue would be
  machinery without a customer until polygons reach tens of km².
- **Authentication.** The API is public read-only over a local network; the admin has a login.

## What to look at

- [`backend/warehouse/queries/low_speed_street_share.sql`](backend/warehouse/queries/low_speed_street_share.sql)
  — one KPI end to end: R-tree scan, `ST_Intersection` clipping, the denominator choice, the
  breakdown and the context in one statement.
- [`backend/apps/areas/resolve.py`](backend/apps/areas/resolve.py) — the resolver computes
  *drawn ∩ district* once (`effective_wkt`); every KPI and layer runs on that.
- [`backend/pipeline/derive_bands.py`](backend/pipeline/derive_bands.py) — how every uncited
  band boundary was derived (grid, minimum denominator, P33/P67), and the sidewalk-coverage
  measurement that changed the pedestrian KPI's definition.
- [`docs/reference-areas/`](docs/reference-areas/) — the two polygons behind the A/B table in
  NOTES. The drawn area lives in the URL, so open them directly:
  **A, Sant Antoni superblock:** `http://localhost:5173/?area=2.15326,41.38205,2.15668,41.38457,2.16331,41.37945,2.15989,41.37693`
  **B, Aragó corridor:** `http://localhost:5173/?area=2.17846,41.40463,2.18181,41.40206,2.17503,41.39706,2.17168,41.39963`
- [`backend/warehouse/connection.py`](backend/warehouse/connection.py) — one connection per
  process, a cursor per request, and a stat-guarded reopen so `make load-data` and rebuilds
  are picked up by a running server.
- [`frontend/src/features/map/layers.ts`](frontend/src/features/map/layers.ts) —
  `emphasisExpression`: the whole of "a chart click filters the map", a pure function applied
  as a paint property, never a refetch.
- [`frontend/src/features/dashboard/contribution.ts`](frontend/src/features/dashboard/contribution.ts)
  — one pure rule per KPI for "what does this feature contribute", from the loaded layer.

## Tests

`make test` runs both suites inside the containers (40 backend, 33 frontend; nothing hits
the network or needs the real extract).

- The test that pins a KPI computation:
  [`backend/tests/test_kpis.py::test_low_speed_share_is_length_weighted_over_mapped_carriageway`](backend/tests/test_kpis.py)
  — three 100 m segments at 30 / 50 / no limit on a synthetic warehouse must read exactly
  50.0 %; change the class list, the clipping or the length function and it fails. Every KPI
  has one.
- The frontend test: [`frontend/tests/App.test.tsx`](frontend/tests/App.test.tsx) — with MSW
  mocking the API, setting a drawn area in the store updates every card to the new values,
  clearing returns to the district, and `sample_size: 0` renders the empty state.
- Also: a real-district regression pinning all five values to two decimals, a two-thread
  isolation test on the shared connection, the 503 → build → 200 and rebuild → new numbers
  paths, every 422 case, cache invalidation on an admin edit, and the pure seams (draw
  finish, highlight expressions, contribution rules, band ramp).

## Findings worth knowing

- **DuckDB `ST_Transform` follows EPSG axis order.** EPSG:4326 is (lat, lon), so a transform
  without `always_xy := true` puts Barcelona 4 700 km away with plausible-looking numbers.
- **`access_restrictions` hides one-way rules.** The dominant entry is `denied` +
  `heading = 'backward'` with no mode; reading it as "closed" removes 80 % of residential streets.
- **DuckDB caches database instances per path.** Reopening a replaced warehouse file while the
  old connection is alive silently returns the old instance; the handle drains cursors and
  closes first.
- **`list()` ignores a CTE's `ORDER BY`.** Breakdown order came out thread-dependent on ties;
  the sort now lives inside the aggregate.
- **A polygon containing the district read different numbers than the district.** Segments
  that touch the district are stored whole; clipping to the raw drawing counted their outside
  parts. Every KPI now runs on drawn ∩ district, pinned by a regression test.
- **The pedestrian KPI was measuring sidewalk mapping.** Overture carries about half of
  Eixample's sidewalks as separate lines (0.7–1.5 km per carriageway km across cells), so the
  "share of network that is pedestrian" sat at 50–55 % everywhere — its variance was OSM
  coverage. Sidewalks and crosswalks are now excluded; the district reads 20.6 %, not 52 %.
- **Overture already carries the Sant Antoni superblock.** Comte Borrell and Consell de Cent
  are `living_street` at 10 km/h; the superblock reads 63.6 % calmed against 47.7 % on an
  equal-sized Aragó corridor. No data lag to report there.

## Walkthrough

[`walkthrough/walkthrough.pdf`](walkthrough/walkthrough.pdf) — twelve slides: the district
read, the two reference areas, what the numbers do not claim, where every threshold comes
from, the three times the data measured the mappers, architecture, rejected alternatives,
the SQL, four bugs worth knowing, and what breaks at 10×. Source: `walkthrough/deck.md`,
exported with `make deck` (Marp, via Docker; the PDF is committed so no one has to).

Architecture and conventions: [`CLAUDE.md`](CLAUDE.md). Reconnaissance evidence:
[`docs/recon.md`](docs/recon.md). Configuration: [`.env.example`](.env.example).
