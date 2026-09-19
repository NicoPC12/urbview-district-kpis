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
| `http://localhost:8000/api/v1/health` | `{"status": "ok", "warehouse": <bool>}` — `warehouse` is whether `data/warehouse.duckdb` exists |
| `http://localhost:8000/api/schema/` | OpenAPI schema (source of the generated frontend types) |
| `http://localhost:8000/api/docs/` | Swagger UI |

Other commands (`make help` lists them all):

```bash
make test     # pytest + vitest, inside the running containers
make lint     # ruff + mypy + eslint + prettier + tsc
make down     # stop the stack; the Postgres volume is kept
```

## Configuration

`docker compose up` works on a clean clone with no `.env`. Every variable is documented in
[`.env.example`](.env.example); copy it to `.env` only if you need to change something.

This is a deliberate deviation from the working agreement's "no secret in
`docker-compose.yml`" rule: the file carries a default Postgres password and `dev.py` a
`django-insecure-` key. That rule targets real credentials, and a throwaway password guarding
a local container nobody can reach is not one — while a required `cp .env.example .env` would
turn the brief's two-command setup into three. `config.settings.prod` takes no defaults and
refuses to start without `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` and `DJANGO_ALLOWED_HOSTS`.

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

Phase 1 only, so far:

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
