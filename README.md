# UrbView — district KPI dashboard

A single page showing a map of a Barcelona district next to a KPI dashboard. Drawing a
polygon on the map recomputes every KPI for that polygon alone. Data source: Overture Maps,
and nothing else.

> **Status:** Phase 1 (infrastructure) complete. The map, the KPIs and the data pipeline are
> not built yet; the page currently shows the app name and the backend health probe.

## Prerequisites

- Docker Desktop (tested with Docker 29 / Compose v5 on Windows 10).
- GNU `make` — on Windows: `winget install GnuWin32.Make`, then run from Git Bash.
- Nothing else. Python and Node run inside the containers.

## Setup

```bash
docker compose up --build   # 1. app on http://localhost:5173, API on http://localhost:8000
make load-data              # 2. fetch the Overture extract and build the warehouse (Phase 2)
```

Measured cold `docker compose up --build` on a machine with no cached images: **2 min 50 s**,
plus ~10 s until Postgres is healthy and migrations have run.

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
  pipeline/       Overture extraction + warehouse build        — Phase 2
  tests/          pytest
frontend/
  src/api/        typed client + hooks (schema.gen.ts arrives with `make types`)
  src/state/      zustand store — the single source of truth   — Phase 5
  src/features/   map/, dashboard/, area/                      — Phase 5
  src/components/ui/  presentational primitives
  src/lib/        pure helpers
  tests/          vitest + testing-library + msw
data/             GITIGNORED — produced by `make load-data`
walkthrough/      deck source + exported PDF                   — Phase 8
docker-compose.yml, Makefile, NOTES.md (Phase 7)
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
