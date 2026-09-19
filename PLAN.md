# PLAN.md

Delivery plan for the UrbView take-home. Read `CLAUDE.md` first for the rules; this file is
the order of operations.

**Due:** Friday 25 September, 14:00 CEST — a Git repository link plus the walkthrough PDF.
**Stated budget:** 8–10 hours. **Honest estimate below:** ~12 h. §12 is the cut ladder for
getting back under budget.

---

## 0. Effort allocation

Derived from the published rubric. Do not let the backend eat the frontend's hours — it is
the classic failure mode on this kind of task and it costs 25% of the grade to save 20%.

| Area | Rubric | Target hours |
|---|---|---|
| Frontend + dashboard | 25% | 3.0 |
| Judgment about the numbers (KPI choice, thresholds, NOTES.md) | 20% | 1.5 |
| Backend + data access | 20% | 2.5 |
| Walkthrough deck | 15% | 1.5 |
| Tests + runnability | 12% | 1.5 |
| Docs + extraction | 8% | 1.0 |
| Recon + scaffolding (overhead, unavoidable) | — | 1.0 |

**Principle from the brief, quoted so it does not get forgotten:** *if something has to
give, cut KPIs — not the drawing, not the tests, not the walkthrough.*

---

## Phase 0 — Reconnaissance and decisions (1.0 h)

Nothing gets built until we know what Overture actually carries in the chosen district.
Choosing KPIs before looking at the data is how you end up with a dashboard full of zeroes.

**Tasks**
1. Pick the district. Default: **Barcelona — Eixample** (~7.46 km², the brief's own example,
   and a place we can sanity-check on foot). Fallbacks if the data is thin: Gràcia (~4.2 km²)
   or Ciutat Vella (~4.4 km²).
2. Get the district polygon from Overture `division_area`. Barcelona districts may sit under
   `subtype=borough` or `neighborhood` — inspect rather than assume. **If Overture has no
   usable polygon for the district, fall back to a hardcoded bbox and write that down in
   NOTES.md as a data finding.** Do not fetch the boundary from anywhere else.
3. Run a throwaway DuckDB count script over the district bbox for every candidate theme:
   segments, connectors, places, buildings, land_use, water, infrastructure
   (`subtype=utility`, `class=street_lamp`), transit-related features. **Record the counts** —
   they go straight into the walkthrough as evidence.
4. Lock the KPI set against those counts. Candidates, in preference order:

   | Candidate | Type | Needs | Risk |
   |---|---|---|---|
   | `lit_street_share` — street length within *r* m of a lamp | share + distance | `infrastructure` lamps, `segment` | **High** — lamp coverage in Overture is OSM-derived and patchy. Verify in step 3. Its caveat is excellent material if the data is there. |
   | `junction_density` — junctions per km² | density | `connector`, `segment` | Low — always computable. |
   | `walkable_network_share` — share of network length open to pedestrians | share | `segment` (class, access restrictions) | Low. |
   | `green_water_share` — share of area that is park, green or water | share | `land_use`, `water` | Low. |
   | `land_use_mix` — Shannon entropy of land use / place categories | index | `land_use` or `places` | Medium — needs a defensible binning. |
   | `transit_distance_p50` — median building distance to nearest transit stop | distance | transit stops in `places`/`infrastructure` | **High** — verify stops exist before committing. |

   **Ship 4, keep a 5th as stretch.** The set must include at least one share, one density
   and one distance (rubric: "at least one KPI that is more than a count").
5. Write the chosen set, with thresholds and sources, into a first draft of `NOTES.md`
   **now**, before implementing. Implementing first and rationalising after is how honest
   citations turn into invented ones.

**Checkpoint:** `docs(notes): first draft of KPI table with sources`
**Exit criterion:** every chosen KPI has non-trivial feature counts in the district, and
every threshold has either a URL or the word "chosen" next to it.

---

## Phase 1 — Repository and infrastructure (1.0 h)

**Tasks**
1. Monorepo skeleton per `CLAUDE.md` §4. `.gitignore` covering `data/`, `*.duckdb`,
   `*.parquet`, `.env`, `node_modules`, `__pycache__`.
2. `backend/`: Django 5 project, `config/settings/{base,dev,prod}.py`, `django-environ`,
   DRF, `drf-spectacular`, `ruff`, `mypy`, `pytest-django`. Health endpoint.
3. `frontend/`: Vite + React + TS strict + Tailwind + ESLint + Vitest. Blank page that
   renders.
4. `docker-compose.yml`: `db` (postgres:16), `backend`, `frontend`. Named volume for
   Postgres. `data/` bind-mounted into the backend. Healthchecks so `backend` waits on `db`.
5. `Makefile` with every target from `CLAUDE.md` §11 (stubs are fine for now).
6. `README.md` skeleton with the setup section filled in — update it as things land, do not
   leave it for the last hour.

**Checkpoint:** `docker compose up` gives a reachable API health endpoint and a blank page.
Commit as several commits, not one.

---

## Phase 2 — Extraction pipeline (1.5 h)

**Tasks**
1. `pipeline/extract.py` — pull the district's bbox from Overture S3 GeoParquet. Either the
   `overturemaps` CLI (`overturemaps download --bbox=… -t segment -f geoparquet -o …`) or
   DuckDB `httpfs` reading `s3://overturemaps-us-west-2/release/<RELEASE>/theme=*/type=*/*`
   with a `bbox.xmin/xmax/ymin/ymax` filter for predicate pushdown. **Pin the release
   string** and record it in the response `meta` — results must be reproducible.
   Types needed: `segment`, `connector`, `place`, `building`, `land_use`, `water`,
   `infrastructure`, `division_area`.
2. `pipeline/build.py` — build `data/warehouse.duckdb` from `data/raw/`:
   - `INSTALL spatial; LOAD spatial;`
   - clip each theme to the district polygon;
   - keep `geom` (EPSG:4326, for serving) **and** `geom_m = ST_Transform(geom, 'EPSG:4326',
     'EPSG:25831')` (for every metric computation);
   - pre-compute stable per-row values: segment length in metres, building centroid,
     connector degree;
   - `CREATE INDEX … USING RTREE (geom_m)` on every table. Note the DuckDB limitation: the
     R-tree is used only when one side of the spatial predicate is a constant — which is
     exactly our case (the drawn polygon). Worth a line in the walkthrough.
3. `make load-data`: by default downloads a **prepared extract** published as a GitHub
   Release asset and runs `build.py`; `make extract` re-runs the real Overture pull.
   Rationale to put in the README: the brief demands both "commit the extraction script, not
   the data" *and* "fifteen minutes from clean clone to running app". A release asset
   satisfies both — nothing large in Git history, and the reviewer is not waiting on S3.
   **Ask them to confirm this is acceptable (see §13).**
4. Idempotent: running it twice produces the same warehouse, and re-running does not
   re-download if the file is present and its checksum matches.

**Checkpoint:** `make load-data` on a clean machine produces a warehouse and prints a table
of row counts per theme. Time it and record the number.

---

## Phase 3 — KPI engine (2.0 h)

**Tasks**
1. `warehouse/connection.py` — read-only connection factory, `spatial` loaded, sane
   `memory_limit` and `threads`. Connection reuse per process; DuckDB is not thread-safe
   across a single connection, so use a small pool or a per-request cursor.
2. Area resolution in `apps/areas/`: district slug | bbox | GeoJSON polygon → one validated
   WKT polygon. Validation: valid geometry, not self-intersecting, area cap (reject > ~50 km²
   with a 422), intersects the loaded district.
3. Register the area once per request as a temp table with both `geom` and `geom_m`. Every
   KPI SQL joins against it. One projection per request, not one per KPI.
4. `warehouse/queries/*.sql` — one file per KPI, contract per `CLAUDE.md` §8. Each does its
   own clipping (`ST_Intersection`) so a segment half inside the polygon contributes half
   its length, not all or nothing. **Say so explicitly in NOTES.md — it is a real
   methodological choice and reviewers will look for whether it was considered.**
5. `apps/kpis/registry.py` — the `KpiDefinition` dataclasses, bands, sources, `not_claim`.
6. `apps/kpis/engine.py` — run the registry over an area, assemble values, bands, legend and
   layers.
7. `insights.py` — rule-based sentence generation. A rule fires on a value range and formats
   a sentence containing computed numbers. At least three rules, so different areas produce
   different sentences. Anything that always returns the same string is hardcoding.

**Checkpoint:** a Django shell call returns a full, correct response dict for the whole
district. Log and record the timing.

---

## Phase 4 — API layer (1.0 h)

**Tasks**
1. `POST /api/v1/kpis` per the contract in `CLAUDE.md` §6.
2. Serializers with full `drf-spectacular` annotations — the OpenAPI schema is the source of
   truth for the frontend types, so an unannotated field is an invisible field.
3. Error handling: RFC 7807 problem details, 422 for invalid geometry/oversized area,
   500 never leaking a stack trace.
4. Response caching keyed by `sha256(normalised area WKT + registry version)`. Locmem in
   dev is fine; note Redis as the production answer in the walkthrough.
5. Django models + migrations: `District`, `KpiDefinition` (key, label, unit, definition,
   not_claim, bands JSON, source JSON). Seed via a data migration or a management command.
   **Serving thresholds and citations from the database rather than hardcoding them in the
   frontend is the concrete mechanism behind the "judgment" rubric line** — make that
   argument in the deck.
6. `make types` → `openapi-typescript` → `frontend/src/api/schema.gen.ts`, committed.

**Checkpoint:** `curl` with a drawn polygon returns a correct response; `/api/schema/`
serves valid OpenAPI; generated types compile.

---

## Phase 5 — Frontend (3.0 h) — the highest-weighted phase

Build in this order. Each step is demoable, so a time overrun still leaves something
coherent.

**5.1 Map shell (0.5 h)**
MapLibre with a free raster/vector basemap (no token — a reviewer without an API key must
still see a map). District polygon rendered, fit bounds.

**5.2 Store + data fetching (0.5 h)**
Zustand store per `CLAUDE.md` §7, TanStack Query hook `useKpis(area)` typed from
`schema.gen.ts`. Dashboard renders raw values in a list. **Both views already share one
state before either gets styled** — retrofitting this later is the expensive mistake.

**5.3 Drawing (0.5 h)**
`terra-draw` + `terra-draw-maplibre-gl-adapter`. Polygon mode, one shape at a time, a clear
"Clear drawing" affordance returning to the whole district. Drawing completion sets
`area` → every KPI refetches. **This is the core interaction — it works before anything is
made pretty.**

**5.4 Dashboard (0.8 h)**
KPI cards: value, unit, band pill coloured by band, definition, and the `not_claim` visible
(tooltip or secondary line — visible, not hidden in a modal). One Recharts chart driven by a
KPI `breakdown`. Insights block. Legend from the API.

**5.5 Bidirectional interaction (0.5 h)**
- Dashboard → map: click a chart segment or legend item → `selectedCategory` → matching
  features highlighted via MapLibre filter expressions, others dimmed.
- Map → dashboard: click a feature → `selectedFeatureId` → dashboard panel shows that
  feature's contribution, computed client-side from the loaded layer.

**5.6 States and polish (0.2 h)**
Loading skeletons per card. Empty state ("no lamps in this area" — with the honest note that
this may mean unmapped, not absent). Error state with retry. Invalid-polygon message.
Responsive down to a laptop screen; mobile is not required and saying so in the README is a
better use of time than half-doing it.

**Checkpoint:** record a screen capture of draw → recompute → click-through. It is the deck's
best slide and the fastest way to check nothing regressed later.

---

## Phase 6 — Tests (1.5 h)

Per `CLAUDE.md` §10.

1. Synthetic fixture built in code: two 100 m segments, one lamp 10 m from the first. Assert
   `lit_street_share == 50.0` exactly. Hand-verifiable, and it fails if the radius, the
   projection or the length function changes.
2. Regression test pinning every KPI on the real district to 2 decimals.
3. Empty-polygon test: 200, `value: null`, `sample_size: 0`.
4. Validation test: self-intersecting polygon → 422.
5. Frontend (Vitest + RTL + MSW): drawing a polygon updates the displayed values; empty
   state renders on `sample_size: 0`.

**Checkpoint:** `make test` green from a clean container.

---

## Phase 7 — NOTES.md and README (1.0 h)

**NOTES.md** — a reference table, not an essay. One row per KPI:

| Column | Content |
|---|---|
| KPI | key + label |
| What it measures | one sentence |
| How it is computed | the formula in words, plus the denominator used and why |
| Thresholds | the band boundaries |
| Source | URL, or "chosen — because …" |
| What it does not claim | one sentence, the most important column on the page |

Plus short sections on: the clipping rule (partial features contribute proportionally), the
projection choice (EPSG:25831 and why not 3857), Overture coverage gaps found in Phase 0
with the actual counts, and the denominator policy.

**README.md** — setup (the two commands), what was built, **what was cut and why**, and a
"what to look at" section pointing the reviewer at the bits worth their time. The brief asks
for the cut list explicitly; a confident one reads as judgment, not as an excuse.

---

## Phase 8 — Walkthrough deck, 8–12 slides (1.5 h)

They read this first. Slide plan:

1. **The place and the question.** District, size, why this one.
2. **The dashboard reading a real place.** Screenshot of the whole district, with what the
   numbers say about it.
3. **A drawn area.** Screenshot of an interesting polygon and how the numbers move — pick
   somewhere with a genuine story (a superblock vs a through-route, a park edge). *This is
   the slide the whole deck exists for.*
4. **The KPIs and where the thresholds come from.** Table, with the citations visible and
   the "chosen" ones honestly labelled.
5. **What these numbers do not claim.** A whole slide on it. It is 20% of the grade and the
   thing most candidates will treat as a footnote.
6. **Architecture diagram.** Extraction → storage → query → client.
7. **Why DuckDB over PostGIS, and why REST over GraphQL.** Rejected alternatives, with the
   reasoning.
8. **Where the computation happens.** Show a KPI SQL file. Make the point that clipping and
   aggregation are in the engine, and what the Python-loop version would have cost.
9. **Component boundaries.** Why `warehouse/` knows nothing about Django, why map and
   dashboard share one store.
10. **What breaks at 10×.** Honest and specific: DuckDB single-file limits, partitioning by
    district/theme, precomputing KPIs on an H3 grid, moving to async + a job queue when the
    computation goes past a few seconds, streaming vector tiles instead of GeoJSON payloads,
    caching keyed by polygon hash, cache invalidation on Overture release.
11. **Another week / what I would throw away.** Concrete on both sides.

Export to PDF, commit under `walkthrough/`.

---

## Phase 9 — Dry run and submission (0.5 h)

1. Clone into a fresh directory. `docker compose up`, then `make load-data`. **Time it.** If
   it exceeds fifteen minutes, fix that before anything else — it is a graded gate.
2. `make lint && make test` clean.
3. Review the commit history: no secrets, no data files, messages readable.
4. `git log --oneline | wc -l` — if it is under ~20, the history does not look like work.
5. Send: repository link + walkthrough PDF, with a short note listing what was cut.

---

## 10. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Overture carries almost no street lamps in the district | High | Detected in Phase 0 before any code. Either swap the KPI or keep it *and make the coverage gap the finding* — that is a legitimate, even strong, result under the one-source rule. |
| No transit stops in Overture for the district | Medium | Same: Phase 0 counts decide. Drop `transit_distance_p50` rather than reaching for GTFS. |
| District polygon missing from `division_area` | Medium | Hardcoded bbox fallback, documented in NOTES.md. The brief says a hardcoded city is fine. |
| DuckDB `ST_Transform` / PROJ friction in the Docker image | Medium | Verify in Phase 1, not Phase 3. If it fights back, reproject once in the build step with GeoPandas — the *build* is allowed to be slow and un-clever; the *query path* is not. |
| Frontend squeezed by backend overrun | High | Phase 5 is time-boxed and ordered so partial delivery still demos. If Phase 3 or 4 overruns, cut a KPI immediately (§12). |
| Payload size — full district GeoJSON is heavy | Medium | Simplify geometry server-side at a fixed tolerance, round to 6 decimals, cap returned features and report the cap in `meta`. Say in the deck that vector tiles are the real answer. |
| 15-minute setup blown by the Overture download | Medium | Prepared extract via release asset (Phase 2.3). |
| Scope creep into "extras" | High | The brief says there is no penalty for adding none. Extras only after every must-have is green. |

---

## 11. Deliverables checklist

- [ ] Django backend, endpoint accepting polygon / bbox / district id, returning KPIs + geometry
- [ ] Clipping and aggregation in DuckDB, not in Python
- [ ] Migrations that run
- [ ] React + TypeScript + MapLibre single page, map and dashboard on one state
- [ ] Draw a polygon → every KPI recomputes; clearing returns to the district
- [ ] At least one chart
- [ ] At least one KPI that is a share, density or distance
- [ ] Dashboard → map highlight, and map → dashboard contribution
- [ ] Loading, empty, error and invalid states
- [ ] Types generated from the schema, not hand-written
- [ ] `NOTES.md` reference table with thresholds, sources and a "does not claim" per KPI
- [ ] Walkthrough PDF, 8–12 slides
- [ ] `docker compose up` + one documented data-load command
- [ ] A test that pins a KPI computation, and a frontend test
- [ ] Clean clone to running app in under 15 minutes, verified
- [ ] Extraction script committed, data not
- [ ] README with setup, what was built, and what was cut
- [ ] Real commit history

---

## 12. Cut ladder

If time runs short, cut strictly in this order:

1. The 5th (stretch) KPI.
2. The 4th KPI. **Three well-argued KPIs with citations beat five thin ones** — this is
   stated in the brief.
3. Visual polish: animations, custom basemap styling, dark mode.
4. Response caching.
5. The regression test on the real district (keep the synthetic pin — that is the graded one).

**Never cut:** the drawing interaction, the bidirectional interaction, the tests, the
walkthrough, the "does not claim" fields, the 15-minute setup.

---

## 13. Questions to send them now

The email says they would rather answer than have us guess. Ask on day one — the answers
change the plan, and asking is itself a signal.

1. Is a **prepared Overture extract published as a release asset** acceptable for the
   data-load command, with the extraction script committed and re-runnable, given the
   fifteen-minute setup requirement? Or do they want `make load-data` to hit S3 every time?
2. **REST + OpenAPI with generated TypeScript types** instead of GraphQL — does that satisfy
   the "generated rather than hand-written" intent, or do they specifically want to see
   GraphQL codegen?
3. If Overture's coverage for a theme in the chosen district is very sparse, do they prefer
   the KPI **kept with the gap reported as a finding**, or **dropped**?
4. Should the walkthrough PDF live in the repository, or be sent separately?

---

## 14. Review call preparation (after submission, ~1 h)

Not part of the repository, but it is graded in practice.

- **The live change.** Fifteen minutes where they ask for a modification while watching.
  Most likely: add a KPI, make a chart click filter the map, or debug a slow polygon. The
  KPI contract in `CLAUDE.md` §8 exists to make the first one a five-minute job — rehearse
  it once end to end.
- **Know the slow path.** Be able to answer "why does this take nine seconds on a 10 km²
  polygon" with a real diagnosis: R-tree not used because the predicate argument was not
  constant, geometry re-projected per row, GeoJSON serialisation dominating, no cache hit.
- **Be able to defend every threshold from memory**, including which ones were chosen rather
  than cited. An honest "I picked that, here is my reasoning" is an accepted answer; a
  half-remembered standard is not.
- **Stripe / SaaS billing, last fifteen minutes.** Nothing to build. Be ready to talk
  through: webhook idempotency and replay, verifying signatures, keeping subscription state
  in step with the provider when a webhook is missed or arrives out of order (reconciliation
  job vs trusting the event stream), the `checkout.session.completed` vs
  `invoice.paid` ordering trap, proration and plan changes, and treating Stripe as the
  source of truth for billing state while the local DB is a read-optimised projection.
