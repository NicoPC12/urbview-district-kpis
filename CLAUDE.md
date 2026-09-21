# CLAUDE.md

Working agreement for this repository. Read this before writing any code.

---

## 1. What this is

A take-home technical task for **UrbView** (Barcelona, urban safety intelligence).

**The product in one sentence:** a single page showing a map of a city district next to a
KPI dashboard, where drawing a polygon on the map recomputes every KPI for that polygon
alone.

**Deadline:** Friday 25 September, 14:00 CEST. **Budget:** 8–10 hours of work, walkthrough
included. **Data source:** Overture Maps, and nothing else.

**How it is graded** (published by the company — spend effort proportionally):

| Dimension | Weight | What they look for |
|---|---|---|
| Frontend and dashboard | 25% | Map + dashboard share one state. The drawn area genuinely drives the numbers. Interaction reads both ways. Types generated, not hand-written. |
| Judgment about the numbers | 20% | Every threshold traced to a source, or an honest "I chose this". Each KPI says what it does *not* claim. |
| Backend and data access | 20% | Clipping and aggregation pushed into the query engine, not a Python loop. Sensible indexing/partitioning. Migrations run. No N+1. |
| The walkthrough | 15% | Shows the product reading a real place. Explains decisions *and rejected alternatives*. Knows what breaks at 10× size. |
| Tests and runnability | 12% | A test that fails if a KPI's computation changes. Clean clone → running app in under 15 minutes. |
| Docs and data extraction | 8% | `NOTES.md` is a usable reference table. Overture pull scripted and committed, the data not. |

---

## 2. Hard rules — never break these

1. **Overture Maps is the only data source.** No OpenStreetMap, no municipal open data, no
   GTFS, no second dataset to patch a gap. If Overture does not carry something, that
   absence is a finding to report, not a problem to work around.
2. **No socioeconomic data of any kind.** Not income, rent, education, unemployment,
   deprivation indices, nationality, ethnicity, migration background, age structure,
   household composition, health, insurance or lending data. Not as a KPI, not as a
   denominator, not as a control variable. Legal denominators: **street length, area,
   building count, segment count**. State which one was used and why.
3. **Every threshold is traceable.** A KPI band boundary either cites a checkable source
   (standard, paper, municipal guideline, with a URL) or is explicitly marked
   `source.kind = "chosen"` with the reasoning written down. A fabricated or
   approximately-remembered citation is worse than no citation. If unsure a source says
   what we claim, mark it `chosen` and explain.
4. **Every KPI declares what it does not claim.** This is a required field on the KPI
   definition and it is rendered in the UI, not buried in a doc. A low reading must never
   be presentable as "this place is dangerous".
5. **No Python loops over geospatial features.** Clipping, spatial joins, length, area and
   distance computation happen in DuckDB SQL. Python assembles the response; it does not
   iterate geometries. `for feature in features:` over Overture data is an automatic
   rejection of the change.
6. **Never commit data.** `data/` is gitignored. Extraction scripts are committed; their
   output is not. No `.parquet`, `.duckdb`, `.geojson` fixtures larger than a few KB.
7. **Distances are computed in a projected CRS, never in degrees.** Overture ships
   EPSG:4326. The warehouse build reprojects to **EPSG:25831** (ETRS89 / UTM zone 31N,
   correct for Barcelona) and stores both `geom` (4326, for serving GeoJSON) and `geom_m`
   (25831, for every metric computation). A query that measures metres against 4326
   geometry is a bug even if it runs.
8. **Real commit history.** Conventional Commits, small and logical. One `initial commit`
   containing the whole project is explicitly called out as a failure in the brief.
9. **Every ST_Transform passes `always_xy := true`.** EPSG:4326 is officially
   (lat, lon) and DuckDB honours that, so ST_Transform(ST_Point(lon, lat), ...)
   without the flag silently swaps the axes and returns plausible, wrong
   coordinates. Verified in Phase 1: Barcelona lands ~4 700 km from itself.
   A transform without the flag is a bug even when the numbers look reasonable.

---

## 3. Stack — decided, do not swap

| Layer | Choice | Why (be able to defend this in the review call) |
|---|---|---|
| Backend | **Django 5 + Django REST Framework** | Required by the brief. |
| API style | **REST + OpenAPI** (`drf-spectacular`) | GraphQL was rejected: the only rubric advantage is generated client types, which `openapi-typescript` gives us for a fraction of the setup cost inside a 10-hour budget. Documented as a deviation in the README. |
| Geospatial store | **DuckDB + GeoParquet** (`spatial` extension) | The company states they read Parquet with DuckDB rather than keeping geometry in Postgres. Also the natural extraction path from Overture's S3 GeoParquet — one engine end to end. |
| Relational store | **PostgreSQL** (Django ORM only) | Holds the district catalogue and KPI definitions/thresholds/citations. Gives us real migrations. **No geometry lives here.** |
| Frontend | **Vite + React 18 + TypeScript (strict)** | Vite, not Next.js: no SSR need, and it is the fastest clean-clone-to-running path. |
| Map | **MapLibre GL JS v5** | Required by the brief. |
| Drawing | **`terra-draw` + `terra-draw-maplibre-gl-adapter`** | MapLibre-native, TypeScript-first, actively maintained. `mapbox-gl-draw` needs a compatibility shim. |
| Charts | **Recharts** | Cheapest path to one good chart. |
| Styling | **Tailwind CSS** | |
| Server state | **TanStack Query** | Keyed by the area selection; gives loading/error/empty states for free. |
| Client state | **Zustand** | One store for area + selection. See §7. |
| API types | **`openapi-typescript`** generated into `frontend/src/api/schema.gen.ts` | Never hand-write a response type. The generated file is committed and regenerated by `make types`. |
| Backend tests | **pytest + pytest-django** | |
| Frontend tests | **Vitest + Testing Library + MSW** | |
| Python tooling | **ruff** (lint + format), **mypy** (strict on `warehouse/` and `kpis/`) | |

---

## 4. Repository layout

```
.
├── backend/
│   ├── config/                 # Django project: settings/, urls.py, asgi.py
│   ├── apps/
│   │   ├── areas/              # District model, area resolution (id | bbox | polygon)
│   │   └── kpis/               # KPI registry, engine, serializers, views
│   ├── warehouse/              # DuckDB access layer — ZERO Django imports
│   │   ├── connection.py       # connection factory, extension loading, pragmas
│   │   ├── schema.sql          # warehouse tables + RTREE indexes
│   │   └── queries/            # one .sql file per KPI
│   ├── pipeline/               # Overture extraction + warehouse build
│   │   ├── extract.py          # Overture S3 -> data/raw/*.parquet
│   │   └── build.py            # data/raw/*.parquet -> data/warehouse.duckdb
│   ├── tests/
│   │   ├── fixtures/           # tiny synthetic geometries, hand-checkable
│   │   ├── test_kpis.py
│   │   └── test_api.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                # schema.gen.ts (generated) + typed client + hooks
│   │   ├── state/              # zustand store — the single source of truth
│   │   ├── features/
│   │   │   ├── map/            # MapView, layer builders, draw control, popups
│   │   │   ├── dashboard/      # KpiGrid, KpiCard, chart, insights, legend
│   │   │   └── area/           # area selection logic shared by both
│   │   ├── components/ui/      # dumb presentational primitives
│   │   └── lib/                # pure helpers (formatting, geometry utils)
│   ├── tests/
│   ├── Dockerfile
│   └── vite.config.ts
├── data/                       # GITIGNORED
├── walkthrough/                # deck source + exported PDF
├── docker-compose.yml
├── Makefile
├── README.md
└── NOTES.md
```

**Boundary rules**
- `warehouse/` must not import Django. It is a pure DuckDB data-access library and is
  independently testable. This is the component boundary we argue for in the walkthrough.
- `apps/kpis/` orchestrates: resolve area → call warehouse → assemble response. It contains
  no SQL strings and no geometry maths.
- `features/map/` and `features/dashboard/` must not import from each other. They talk only
  through `state/`. That is what "one state, not two" means in practice.

---

## 5. Architecture and data flow

```
Overture S3 GeoParquet
        │  pipeline/extract.py — bbox pushdown, one file per theme
        ▼
data/raw/*.parquet
        │  pipeline/build.py — clip to district, ST_Transform 4326 -> 25831,
        │                      CREATE INDEX ... USING RTREE
        ▼
data/warehouse.duckdb ──────────────┐
                                    │ read-only connection
PostgreSQL (districts, kpi_defs) ───┤
                                    ▼
                      Django + DRF  /api/v1/kpis
                                    │  JSON: kpis[] + insights[] + legend + layers
                                    ▼
                      React (TanStack Query) ──> Zustand store
                                                  ├─> MapLibre (layers, highlight)
                                                  └─> Dashboard (cards, chart, legend)
```

**Request lifecycle**
1. Client POSTs an area (district slug, bbox, or GeoJSON polygon).
2. `areas` resolves it into a single WKT polygon and validates it (area cap, vertex cap,
   geometry validity). Overlap with the loaded district is *reported*
   (`area.district_overlap_share`), not required: drawing outside is an empty 200.
3. `kpis` takes a cursor on the process-wide read-only DuckDB connection (cursors isolate
   temp objects), registers the area polygon **once** as a temp table, then runs each KPI's
   SQL against it.
4. Results are assembled into the response contract, with definitions, bands and citations
   pulled from Postgres.
5. Response cached by `sha256(normalised area WKT + warehouse build hash + newest
   KpiDefinition.updated_at)` — a rebuild or an admin edit invalidates without clearing.

---

## 6. API contract

`POST /api/v1/kpis`

```jsonc
// request — exactly one of the three
{ "district": "eixample" }
{ "bbox": [2.150, 41.380, 2.180, 41.400] }
{ "polygon": { "type": "Polygon", "coordinates": [[ /* ... */ ]] } }
```

```jsonc
// response
{
  "area": { "name": "Eixample", "km2": 7.46, "source": "drawn" },
  "kpis": [
    {
      "key": "lit_street_share",
      "label": "Street length within 25 m of a lamp",
      "value": 61.4,
      "unit": "%",
      "band": "Partly covered",
      "definition": "One sentence: what this measures.",
      "not_claim": "One sentence: what this explicitly does not tell you.",
      "denominator": "street_length_m",
      "source": {
        "kind": "citation",          // "citation" | "derived" | "chosen"
        "label": "EN 13201-2:2015",
        "url": "https://…",
        "note": "Optional clarification."
      },
      "bands": [
        { "label": "Sparse",         "max": 40 },
        { "label": "Partly covered", "max": 75 },
        { "label": "Well covered",   "max": 100 }
      ],
      "sample_size": 4812,           // features behind the number; drives the empty state
      "breakdown": [                 // optional, feeds the chart and dashboard→map filter
        { "key": "lit",   "label": "Lit",   "value": 61.4, "color": "#16a34a" },
        { "key": "unlit", "label": "Unlit", "value": 38.6, "color": "#b91c1c" }
      ]
    }
  ],
  "insights": [
    "Generated from the data at request time, never hardcoded. Must contain at least one
     computed number and be selected by a rule over the values."
  ],
  "legend": {
    "type": "categorical",
    "items": [{ "key": "unlit", "label": "Unlit", "color": "#b91c1c" }]
  },
  "layers": {
    "vectors": [
      {
        "id": "streets",
        "kpi_key": "lit_street_share",   // links a layer to the KPI it explains
        "data": { "type": "FeatureCollection", "features": [] }
      }
    ]
  },
  "meta": { "computed_ms": 340, "cached": false, "overture_release": "2025-xx-xx.0" }
}
```

**Contract rules**
- `sample_size == 0` is a valid, non-error state. The API returns 200 with `value: null` and
  the UI renders an empty state. A polygon over the sea is not a crash.
- Returned GeoJSON is always EPSG:4326, coordinates rounded to 6 decimals.
- Feature `id` in returned layers is the Overture GERS id, so the map can address features
  with `feature-state` and the dashboard can name them.
- Validation errors return RFC 7807 problem details with a 422.
- Every response field above must exist in the OpenAPI schema — the frontend types are
  generated from it, so an undocumented field does not exist.

---

## 7. Frontend state model

One store. The map and the dashboard are two views of it.

```ts
type AreaSelection =
  | { kind: 'district'; slug: string }
  | { kind: 'drawn'; geometry: GeoJSON.Polygon };

interface AppState {
  area: AreaSelection;              // drives the query key -> drives every number
  selectedCategory: string | null;  // dashboard -> map  (highlight matching features)
  selectedFeatureId: string | null; // map -> dashboard  (show its contribution)
  setArea(a: AreaSelection): void;
  clearArea(): void;                // back to the whole district
  // ...
}
```

Rules:
- KPI data is **never** copied into the store. It lives in TanStack Query, keyed by the
  area. The store holds selection only. Two sources of truth for the same numbers is the
  failure mode this whole section exists to prevent.
- Highlighting is done with MapLibre `feature-state` and filter expressions driven by the
  store. **Never refetch to highlight.**
- Clearing the drawing resets `area` to the district — one action, both views follow.

**The bidirectional interaction is the highest-weighted single feature in the rubric.**
- Dashboard → map: clicking a breakdown category or legend item sets `selectedCategory`;
  matching features change colour and non-matching dim.
- Map → dashboard: clicking a feature sets `selectedFeatureId`; the dashboard shows what
  that feature contributes to the relevant KPI ("this segment: 182 m, 1.4% of unlit length
  in the drawn area"). That contribution is computed client-side from the already-loaded
  layer, not by a second request.

Required states, all implemented: **loading** (skeletons, not a spinner over the whole
page), **empty** (drawn area contains no relevant features), **error** (request failed,
with retry), **invalid** (self-intersecting or oversized polygon).

---

## 8. KPI contract — how to add one

Adding a KPI must be: **one SQL file + one registry entry + one test.** Nothing else.
Keep it that cheap on purpose — the review call includes fifteen minutes of live changes
and "add a KPI" is the most likely ask.

```python
# backend/apps/kpis/registry.py
LIT_STREET_SHARE = KpiDefinition(
    key="lit_street_share",
    label="Street length within 25 m of a lamp",
    unit="%",
    denominator=Denominator.STREET_LENGTH_M,
    definition="Share of drivable and walkable street length whose centreline falls "
               "within 25 m of a mapped street lamp.",
    not_claim="Does not measure how bright a street is, nor whether it is safe. "
              "It measures proximity to lamps that Overture happens to carry.",
    source=Source(kind=SourceKind.CHOSEN, label="…", url=None, note="…"),
    bands=(Band("Sparse", max=40), Band("Partly covered", max=75), Band("Well covered", max=100)),
    sql=SQL_DIR / "lit_street_share.sql",
)
```

Every SQL file:
- receives the clipped area as the temp table `area` (columns: `geom`, `geom_m`);
- returns exactly one row with columns `value`, `sample_size`, and optionally `breakdown`
  (a `LIST(STRUCT(key, label, value))`);
- does all clipping with `ST_Intersection` and all measurement against `geom_m`;
- is readable: CTEs with names, no 200-character lines, a header comment stating the
  formula in words.

**Clipping applies to the measured population, never to the reference universe.**

- Counting and length KPIs (`crossing_density`, `pedestrian_network_share`,
  `low_speed_street_share`) measure **only** features inside the drawn area: partial
  segments contribute proportionally via `ST_Intersection`, points are in or out, and the
  denominator is clipped the same way as the numerator.
- Nearest-neighbour KPIs (`green_space_distance_p50`) clip the **population** — building
  centroids inside the area — but search the **full warehouse** for the nearest target,
  including targets outside the drawn polygon and outside the district. That is why
  `build.py` keeps green spaces 1.5 km beyond the district bbox.

Getting this backwards makes every small drawn polygon return null or infinity, which is
exactly what a reviewer produces in the first thirty seconds of the demo. Every
nearest-neighbour SQL file carries a comment saying which side of this rule it is on, and a
test asserts that a polygon containing buildings but zero green spaces returns a finite p50.

---

## 9. Coding conventions

**Everything in the repository is written in English** — code, comments, commit messages,
docs, variable names, UI copy.

**Python**
- Full type hints. `mypy --strict` clean in `warehouse/` and `apps/kpis/`.
- Google-style docstrings on every public function, class and module. Docstrings say *why*,
  not what the next line obviously does.
- `ruff` for lint and format; line length 100.
- Dataclasses (frozen) for value objects. No dicts flying around as pseudo-types.
- No business logic in views. Views validate, call a service, serialize.
- Settings split: `config/settings/{base,dev,prod}.py`. Secrets from env via
  `django-environ`. No secret ever hardcoded, including in `docker-compose.yml`.

**TypeScript**
- `strict: true`. **`any` is banned**; use `unknown` and narrow.
- API response types are imported from `api/schema.gen.ts`. Hand-writing a type that
  mirrors a response is a bug.
- Components: one component per file, named exports, props interface declared above the
  component. Presentational components in `components/ui/` take no store access —
  they receive props.
- Business logic lives in hooks (`useKpis`, `useAreaSelection`, `useFeatureContribution`),
  not in JSX.
- No magic numbers or hex colours inline — colours come from the API legend or from a
  single theme module.
- TSDoc on every exported hook and non-trivial function.

**Naming**
- `snake_case` in Python and in JSON payloads; `camelCase` in TypeScript at the boundary is
  *not* worth the mapping cost — keep JSON keys `snake_case` and read them as-is. Decide
  once, apply everywhere.

---

## 10. Testing rules

Minimum bar from the brief, treated as non-negotiable:

1. **A test that pins a KPI's computation.** Not that the endpoint returns 200. Build a
   synthetic fixture small enough to verify by hand — e.g. two 100 m street segments and
   one lamp 10 m from the first — and assert `lit_street_share == 50.0`. If someone changes
   the buffer radius or swaps `ST_Length` for something else, this test fails.
2. **A regression test against the real district** pinning each KPI to 2 decimals, so any
   change in the pipeline is visible in a diff.
3. **An empty-area test**: a polygon with no features returns 200, `value: null`,
   `sample_size: 0`.
4. **A frontend test**: with a mocked API (MSW), drawing a polygon updates the dashboard to
   the new values; and the empty state renders when `sample_size` is 0.

Tests must not hit the network or require the full Overture extract.

---

## 11. Commands

```bash
make up            # docker compose up --build   -> app on :5173, api on :8000
make load-data     # THE one documented command from the brief: fetch + build warehouse
make extract       # re-run the real Overture S3 pull from scratch (slow)
make warehouse     # rebuild data/warehouse.duckdb from data/raw/
make types         # regenerate frontend/src/api/schema.gen.ts from the OpenAPI schema
make test          # backend + frontend
make lint          # ruff + mypy + eslint + tsc --noEmit
```

`docker compose up` followed by `make load-data` must take a reviewer from clean clone to
a working app in **under fifteen minutes on a cold machine**. This is a graded requirement.
If a change puts that at risk, say so before making it.

---

## 12. Git conventions

- Conventional Commits: `feat(kpis): add junction density`, `fix(map): …`, `docs(notes): …`,
  `test(kpis): …`, `chore(ci): …`.
- One logical change per commit. Commit at each checkpoint in `PLAN.md`.
- Commit messages in English, imperative mood, body explaining *why* when non-obvious.
- Target: 25–40 real commits by submission.
- **Push after every finished task.** When a task or phase is done, `git push` everything
  before reporting. Unpushed work does not exist for the reviewer.

---

## 13. Ask before you assume

Stop and ask rather than guessing when:

- A threshold would need a citation you are not certain about. Propose
  `source.kind = "chosen"` instead of inventing a standard.
- Overture turns out not to carry something a planned KPI needs. Do not substitute another
  data source. Report the gap and propose replacing the KPI.
- A change would alter an existing KPI's numeric output.
- A change would add a dependency not listed in §3.
- A change would push clean-clone setup past fifteen minutes.
- A refactor would touch more than ~3 files. Prefer targeted edits over rewrites.
- An existing type, constant or interface could be reused — confirm it rather than creating
  a parallel one.

---

## 14. Anti-patterns — reject these on sight

- `for feature in features:` over Overture geometry in Python.
- Computing distance or area on EPSG:4326 coordinates.
- Hand-written TypeScript interfaces mirroring the API response.
- Hardcoded insight sentences pretending to be generated.
- A KPI without a `not_claim`, or with a band boundary and no `source`.
- Fetching data to highlight a feature that is already on screen.
- Dashboard state and map state drifting apart.
- `data/` contents appearing in `git status`.
- Catching an exception and returning fake zeroes. Empty is a state; failure is an error.
- Adding a second data source "just for this one field".
