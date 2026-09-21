# UrbView — district KPI dashboard

A single page showing a map of a Barcelona district next to a KPI dashboard. Drawing a
polygon on the map recomputes every KPI for that polygon alone. Data source: Overture Maps,
and nothing else.

> **Status:** Phases 0–2 complete (reconnaissance, KPI decision, extraction pipeline). The
> warehouse builds; the KPI engine, API and map are not built yet. The page currently shows
> the app name and the backend health probe.

## Prerequisites

- Docker Desktop (tested with Docker 29 / Compose v5 on Windows 10).
- GNU `make` — on Windows: `winget install GnuWin32.Make`, then run from Git Bash.
- Nothing else. Python and Node run inside the containers.

## Setup

```bash
docker compose up --build   # 1. app on http://localhost:5173, API on http://localhost:8000
make load-data              # 2. fetch the prepared Overture extract and build data/warehouse.duckdb
```

Measured on a machine with no cached images: cold `docker compose up --build` **2 min 50 s**
(+ ~10 s to healthy); `make load-data` **9 s** from the release asset, or **~11 min** if it
has to fall back to pulling from Overture's S3 bucket (see "Data" below).

### Data

Overture Maps is the only source. `make load-data` downloads a **prepared extract** — the exact
output of `make extract`, 6.8 MB across six Parquet files — from a GitHub Release asset,
verifies each file against the SHA-256 in [`backend/pipeline/manifest.json`](backend/pipeline/manifest.json),
then builds `data/warehouse.duckdb` (10.5 MB, ~2 s).

The asset lives in a separate, public, data-only repository,
[`NicoPC12/urbview-data`](https://github.com/NicoPC12/urbview-data): the data is not in this
repository because the brief says to commit the extraction script and not the data, and it is
not behind auth because this repository is private and the reviewer's load must work over
plain HTTPS with nothing to configure.

- `make extract` re-runs the real pull from `s3://overturemaps-us-west-2` (release pinned in
  [`backend/pipeline/release.py`](backend/pipeline/release.py)), then builds. ~10 min: the cost
  is S3 row-group scanning, not bytes.
- If the release asset cannot be downloaded (offline, or the data repository is gone),
  `make load-data` falls back to that pull automatically, printing progress every 30 s.
- `make warehouse` rebuilds the warehouse from `data/raw/` without downloading.
- `make publish-extract` (maintainer) uploads `data/raw/*.parquet` and rewrites the manifest.

What the warehouse holds and why only that: [`backend/pipeline/build.py`](backend/pipeline/build.py)
docstring; the reconnaissance behind the choice: [`docs/recon.md`](docs/recon.md).

Useful endpoints:

| URL | What |
|---|---|
| `http://localhost:5173` | The app |
| `POST http://localhost:8000/api/v1/kpis` | Every KPI for `{"district": "eixample"}`, `{"bbox": [...]}` or `{"polygon": <GeoJSON>}` — the contract is in [`CLAUDE.md` §6](CLAUDE.md) and the schema below |
| `http://localhost:8000/api/v1/districts` | District outlines and bounds (what the map draws on load) |
| `http://localhost:8000/api/v1/health` | `{"status": "ok", "warehouse": <bool>}` — `warehouse` is whether `data/warehouse.duckdb` exists |
| `http://localhost:8000/api/schema/` | OpenAPI schema (source of the generated frontend types) |
| `http://localhost:8000/api/docs/` | Swagger UI |
| `http://localhost:8000/admin/` | Django admin: KPI labels, bands and citations are rows, not constants. Login `admin` / `admin` (local default, see Configuration) |

```bash
curl -s --compressed localhost:8000/api/v1/kpis -H 'Content-Type: application/json'   -d '{"polygon":{"type":"Polygon","coordinates":[[[2.160,41.390],[2.170,41.390],[2.170,41.397],[2.160,41.397],[2.160,41.390]]]}}'
```

Before `make load-data` has run, `/api/v1/kpis` answers **503** with an RFC 7807 body whose
`detail` says to run it; once the file appears the same server process serves 200 — no
restart, and the same holds for a later `make warehouse` rebuild (the handle stats the file
and reopens under a lock). Errors are always `application/problem+json`: 422 for an invalid,
oversized (> 50 km²) or over-detailed (> 2,000 vertices) polygon. A polygon drawn *outside*
the district is not an error: it returns 200 with `sample_size: 0` everywhere and
`area.district_overlap_share` says how much of the drawing has data.

Other commands (`make help` lists them all):

```bash
make test     # pytest + vitest, inside the running containers
make lint     # ruff + mypy + eslint + prettier + tsc
make types    # regenerate frontend/src/api/schema.gen.ts from the running backend's OpenAPI schema
make down     # stop the stack; the Postgres volume is kept
```

### Caching

Responses are cached in Django's in-process `locmem` under
`sha256(normalised area WKT + warehouse build hash + newest KpiDefinition.updated_at)`.
Rebuilding the warehouse or editing a threshold in the admin changes the key, so nothing is
ever cleared and nothing is warmed. Honest note: a hand-drawn polygon essentially never
repeats, so the cache serves the district (the one every "clear drawing" returns to) and
exact repeats of a bbox; the drawn path always computes (≈ 0.3–0.5 s for a few blocks).
The cache is per process, so two backend replicas would each compute the district once;
Redis is the production answer and a one-line `CACHES` change.

## Configuration

`docker compose up` works on a clean clone with no `.env`. Every variable is documented in
[`.env.example`](.env.example); copy it to `.env` only if you need to change something.

This is a deliberate deviation from the working agreement's "no secret in
`docker-compose.yml`" rule: the file carries a default Postgres password and `dev.py` a
`django-insecure-` key. That rule targets real credentials, and a throwaway password guarding
a local container nobody can reach is not one — while a required `cp .env.example .env` would
turn the brief's two-command setup into three. `config.settings.prod` takes no defaults and
refuses to start without `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` and `DJANGO_ALLOWED_HOSTS`.

The same convention covers the admin login: the container runs `manage.py ensure_admin` at
start, creating `admin` with `DJANGO_ADMIN_PASSWORD` (dev default `admin`; `prod.py` requires
both `DJANGO_ADMIN_USERNAME` and `DJANGO_ADMIN_PASSWORD`). Between `migrate` and `runserver`
the container also runs `manage.py check --database default`, which refuses to serve if the
KPI keys in code and the `KpiDefinition` rows in Postgres disagree (`kpis.E001`).

## Project structure

```
backend/
  config/         Django project: settings/{base,dev,prod}.py, urls, asgi/wsgi
  apps/areas/     area resolution (district | bbox | polygon)  — Phase 3
  apps/kpis/      KPI registry, engine, serializers, views     — health view today
  warehouse/      DuckDB access layer, zero Django imports     — Phase 3
  pipeline/       release pin, recon, extract, build, load_data, publish
  tests/          pytest
frontend/
  src/api/        typed client + hooks (schema.gen.ts arrives with `make types`)
  src/state/      zustand store — the single source of truth   — Phase 5
  src/features/   map/, dashboard/, area/                      — Phase 5
  src/components/ui/  presentational primitives
  src/lib/        pure helpers
  tests/          vitest + testing-library + msw
data/             GITIGNORED — produced by `make load-data`
docs/             recon.md — Phase 0 evidence and KPI decision
walkthrough/      deck source + exported PDF                   — Phase 8
docker-compose.yml, Makefile, NOTES.md (KPI reference table, first draft)
```

Architecture, KPI contract and conventions: see [`CLAUDE.md`](CLAUDE.md). Order of work:
[`PLAN.md`](PLAN.md).

## What I built

Phases 0–4 so far (frontend next):

- Django 5.2 + DRF + drf-spectacular backend with split settings, PostgreSQL via the ORM,
  a health endpoint that is part of the OpenAPI schema, and a container image with the
  DuckDB `spatial` extension baked in (no network needed at runtime).
- Vite + React 18 + TypeScript (`strict`, `noUncheckedIndexedAccess`) frontend with
  Tailwind v4, ESLint (type-checked), Prettier, Vitest + Testing Library + MSW. One page:
  app name + backend health, with loading / error / values states and three tests.
- Compose stack (`db`, `backend`, `frontend`) with healthcheck ordering, hot reload through
  Windows bind mounts, and a Makefile whose not-yet-implemented targets fail loudly.

- Phase 0 reconnaissance against the real release ([`docs/recon.md`](docs/recon.md)), a
  decided KPI set with verified thresholds ([`NOTES.md`](NOTES.md)), and the extraction
  pipeline: pinned release, district-slice extract, DuckDB warehouse with R-tree indexes,
  checksummed prepared-extract download with S3 fallback.

- The KPI engine: five KPIs as one SQL file each under
  [`backend/warehouse/queries/`](backend/warehouse/queries/), all clipping and measurement in
  DuckDB against EPSG:25831 geometry with R-tree scans, one map layer per KPI, rule-based
  insights, and 38 tests — hand-checkable synthetic pins, a two-decimal district regression,
  and a two-thread isolation test for the shared connection.
- The API: `POST /api/v1/kpis`, `GET /api/v1/districts`, RFC 7807 errors, GZip, a
  self-invalidating cache, and KPI metadata (label, definition, "does not claim", bands,
  source) in Postgres with a seed migration and a Django admin — computation stays in code,
  a system check refuses to start if the two disagree. Frontend types are generated from the
  OpenAPI schema by `make types`.

### Findings worth knowing before Phase 3

**DuckDB `ST_Transform` follows EPSG axis order by default.** EPSG:4326 is officially
(latitude, longitude), so `ST_Transform(ST_Point(2.17, 41.39), 'EPSG:4326', 'EPSG:25831')`
silently returns nonsense (`POINT (5131256 306566)`). With `always_xy := true` it returns the
expected UTM 31N position for Barcelona, `POINT (430608.50 4582384.56)`, and a 0.012° line
due east at that latitude measures 1003 m (analytically ≈1002 m). Every `ST_Transform` in the
warehouse build must pass `always_xy := true`.

## What I cut and why

Nothing yet — nothing has been cut because nothing beyond infrastructure has been built.
This section is filled in as decisions are made.

## What to look at

Nothing to review yet beyond the setup working. This section will point at the KPI SQL, the
shared store, and the tests once they exist.
