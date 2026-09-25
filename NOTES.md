# NOTES — KPI reference

Overture Maps release `2026-08-19.0`, district l'Eixample (Barcelona), 7.508 km². Every
figure below was regenerated on 2026-09-22: KPI figures from the current warehouse, the
"Rejected KPIs" and coverage numbers from a fresh `pipeline/recon.py` run against the same
release (those themes are not loaded into the warehouse). Every band boundary is **cited**
(URL and sentence), **derived** (method in [`docs/derived_bands.md`](docs/derived_bands.md),
re-run with `make derive-bands`) or **chosen** with the reason. The argument belongs in the
walkthrough.

## KPIs

| KPI | What it measures | How it is computed | Bands | Source | What it does **not** claim |
|---|---|---|---|---|---|
| `low_speed_street_share` — *Carriageway limited to 30 km/h or less* | Share of carriageway length inside the area whose posted limit is ≤ 30 km/h. District: **50.7 %**. | Clip carriageway segments (`subtype = 'road'`, class not footway/steps/path/cycleway/pedestrian) to the area with `ST_Intersection`; sum clipped length where the segment's first non-ranged `speed_limits` rule is ≤ 30 km/h; divide by the clipped length that has any mapped limit. **Denominator: carriageway km with a mapped limit** — 11.2 % of carriageway km has no mapped limit (88 % of `service` roads); dividing by all carriageway km would let mapping gaps depress the share. The coverage share (89.0 % district-wide) is returned as context. | ≤ 42 % **Lower third** · ≤ 60 % **Middle third** · > 60 % **Upper third** | **30 km/h — citation.** Real Decreto 970/2020 (BOE-A-2020-13969), new art. 50.1 RGC: "20 km/h en vías que dispongan de plataforma única de calzada y acera; 30 km/h en vías de un único carril por sentido de circulación; 50 km/h en vías de dos o más carriles por sentido" — in force six months after 11 Nov 2020. https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969 . **42 / 60 — derived:** P33 / P67 of the KPI over 125 cells of 250 m (31 cells with < 0.5 km of mapped carriageway dropped), rounded to two significant figures (41.6 → 42, 60.2 → 60). | A posted limit, not an observed speed. Unmapped limits are excluded from both sides, not assumed fast. Says nothing about enforcement, crashes or lane count. Bands are relative to Eixample's own distribution, not an absolute standard. |
| `crossing_density` — *Pedestrian crossings per km of carriageway* | Mapped crossing points per km of carriageway inside the area. District: **22.6 /km** (3,624 crossings, 160.3 km). | Count `infrastructure` points with `class = 'crossing'` inside the area (in or out); divide by clipped carriageway km. **Denominator: carriageway km** — crossings exist to cross carriageways; per km² a polygon over a park would score badly for no street reason. | ≤ 19 **Lower third** · ≤ 26 **Middle third** · > 26 **Upper third** | **Derived.** No standard I could verify prescribes crossings per km. P33 / P67 over 129 cells (27 dropped): 19.5 → 19, 26.2 → 26. | A crossing point has no quality: signalised, raised, marked or lit are unknown. More does not mean safe to cross. A pedestrianised block with no carriageway reads as *no data*, not zero. **In shared-space or living streets, fewer marked crossings can mean the whole street has become crossable; a low reading there is not a deficit.** Bands are relative to Eixample's own distribution. |
| `pedestrian_network_share` — *Street network that is pedestrian-only (sidewalks excluded)* | Share of the mapped street network length inside the area that is pedestrian-only geometry, with sidewalk and crosswalk geometry excluded from both sides. District: **20.6 %** (59.5 of 288.9 km). | Clip every `subtype = 'road'` segment except `subclass IN (sidewalk, crosswalk)`; numerator = clipped length with `class IN (footway, pedestrian, steps, path)`; denominator = all clipped length. **Denominator: street network km** — what share of the street network is given over to walking, which is what a planner can change (pedestrianise a street). **Why sidewalks are out:** Overture maps only about half of Eixample's sidewalks as separate lines — mapped sidewalk km per carriageway km is 1.09 at the median but ranges 0.68 (P10) to 1.54 (P90) across 250 m cells, against ~2 for a fully mapped grid. With them in, the district read 52.1 % and the per-cell values sat in 49.9–55.2 %: the KPI measured OSM sidewalk coverage. Without them it reads 20.6 % and spans 0–71 % across cells. | ≤ 14 % **Lower third** · ≤ 24 % **Middle third** · > 24 % **Upper third** | **Derived.** P33 / P67 over 136 cells (20 dropped): 13.8 → 14, 23.9 → 24. | Street space given over to walking, not sidewalk provision. Says nothing about sidewalk width, quality or continuity. Bands are relative to Eixample's own distribution. |
| `green_space_distance_p50` — *Median distance to a public green space of at least 0.5 ha* | Median straight-line distance from a building centroid inside the area to the nearest mapped public green space ≥ 0.5 ha, wherever it lies. District: **362 m**; 40.7 % of 8,397 buildings within 300 m. | Population = building centroids inside the area (clipped). Targets = `land_use` polygons ≥ 0.5 ha in the **public classes** `park/park`, `park/village_green`, `horticulture/garden` (Barcelona's municipal *Jardins de …*, `leisure=garden` in OSM) and `recreation/recreation_ground` — 159 polygons, searched in the **whole warehouse** (district + 1.5 km), never clipped. Excluded as not public green space (41 polygons): 20 `pitch`, 4 `stadium`, 3 `marina` (Port Olímpic), 9 unnamed `managed/grass`, 3 `agriculture` (a meadow, a farmyard), 1 `plant_nursery`, 1 `track`. **Access was not verified per feature:** `garden` is kept because the named ones here are municipal (*Jardins de Joan Brossa*, *Laribal*, *Mossèn Costa i Llobera*, the Jardí Botànic), but a private garden tagged the same way would also be counted. `ST_Distance` in EPSG:25831 to the nearest; median. **Denominator: building count** — the population is "homes"; Overture has no population, buildings are the legal proxy. | ≤ 300 m **Within WHO rule of thumb** · ≤ 600 m **Beyond** · > 600 m **Far** | **300 m and 0.5 ha — citation.** WHO Regional Office for Europe, *Urban green spaces: a brief for action* (2017), p. 11: "As a rule of thumb, urban residents should be able to access public green spaces of at least 0.5–1 hectare within 300 metres' linear distance (around 5 minutes' walk) of their homes." https://www.who.int/europe/publications/i/item/9789289052498 (PDF via the page's Download link). **600 m — chosen:** double the WHO distance; nothing prescribes a second band. Restricting to public classes moved the district median from 362.03 m to 362.49 m. | Straight-line, not walking distance: a park across a railway reads as near. Only polygons Overture carries count — Eixample's courtyard gardens are largely unmapped, greens under 0.5 ha are ignored by design. **Linear street greening — tree-lined avenues and green axes such as Consell de Cent — is invisible to this KPI by construction: it measures distance to green *areas* of at least 0.5 ha.** Building centroids are not people. |
| `street_tree_density` — *Street trees per km of carriageway* | Mapped individual trees per km of carriageway inside the area. District: **55.4 /km** (8,880 trees). | Count `land` points with `class = 'tree'` inside the area; divide by clipped carriageway km. **Denominator: carriageway km** — street trees line streets; per km² would reward parks twice. | ≤ 20 **Lower third** · ≤ 69 **Middle third** · > 69 **Upper third** | **Derived.** P33 / P67 over 129 cells (27 dropped): 20.2 → 20, 69.0 → 69. | A shade and greenness proxy, not a safety measure. Canopy, species and health unknown; a sapling counts as a plane tree. Tree mapping is OSM-derived and can be uneven outside this district. Bands are relative to Eixample's own distribution. |

`sample_size` is the number of **carriageway segments** (speed, crossings, trees: 1,754 in
the district), **street-network segments** (pedestrian: 3,562) or **buildings** (green:
8,397); the card says which. `value` is `null` when it is 0.

## Derived bands — the method

250 m grid over the district in EPSG:25831, each cell clipped to the district (156 cells);
each KPI computed per cell with the production SQL; cells with **< 0.5 km of denominator**
dropped (**chosen** — one segment would decide the value; drops 20–31 cells per KPI);
cutoffs = 33rd and 67th percentiles of the per-cell values, rounded to two significant
figures. Labels are *Lower / Middle / Upper third* because that is all they mean. Full table:
[`docs/derived_bands.md`](docs/derived_bands.md). The insight sentences read the band, not
their own thresholds, so an admin edit moves them too.

## Two reference areas

Both ~0.32 km², polygons in [`docs/reference-areas/`](docs/reference-areas/) and openable
directly: **A** `/?area=2.15326,41.38205,2.15668,41.38457,2.16331,41.37945,2.15989,41.37693` — Carrer del Comte Borrell from Tamarit to Consell de Cent, 200 m
each side (the Sant Antoni superblock and the Consell de Cent green axis). **B** `/?area=2.17846,41.40463,2.18181,41.40206,2.17503,41.39706,2.17168,41.39963` —
Carrer d'Aragó centred on Carrer de Sardenya, same length and width, east of where the axis
ends.

| KPI | A · superblock (0.318 km²) | B · Aragó corridor (0.317 km²) | District |
|---|---|---|---|
| Carriageway ≤ 30 km/h | **63.6 %** (Upper third) | 47.7 % (Middle) | 50.7 % |
| Crossings / km | 20.9 (Middle) | **31.2** (Upper) | 22.6 |
| Pedestrian-only street network | **26.0 %** (Upper) | 16.7 % (Middle) | 20.6 % |
| Median distance to public green ≥ 0.5 ha | 595 m (Beyond; 0 % within 300 m) | **151 m** (Within; 87 %) | 362 m |
| Street trees / km | 52.7 (Middle) | 50.3 (Middle) | 55.4 |

Overture does carry the intervention: Comte Borrell and Consell de Cent are `living_street`
at 10 km/h for 1.62 km and 2.97 km respectively. **Two rows must not be read as A being
worse.** Crossings: Comte Borrell is shared space at 10 km/h, so the street is crossable
along its length and marked crossings are no longer needed — this KPI *falls* where a
planner has succeeded. Green: the Consell de Cent axis is linear greening, which a
"≥ 0.5 ha polygon" rule cannot see by construction; B's 151 m is Sagrada Família's gardens.
Both caveats are on the cards, and they are why there is no composite score.

## Rules that apply to every KPI

- **Area.** Every KPI and every map layer is measured on *drawn polygon ∩ district* (the
  warehouse stores whole geometries of segments that touch the district). The response
  carries `district_overlap_share` (intersection area / drawn area, in EPSG:25831) and an
  insight says so when it is below 95 %. A polygon entirely outside is a 200 with
  `sample_size = 0`, not an error.
- **Clipping.** Linear features contribute the length of their part inside the area
  (`ST_Intersection`); points are in or out; the denominator is clipped like the numerator.
  Nearest-neighbour targets (green spaces) are never clipped and are searched beyond the
  area and beyond the district — that is why the extract keeps them 1.5 km past the bbox.
- **Projection.** Every metre in EPSG:25831 (ETRS89 / UTM 31N); every `ST_Transform` passes
  `always_xy := true` (DuckDB otherwise honours EPSG's lat-lon axis order for 4326 and puts
  Barcelona 4 700 km away). Never EPSG:3857: its scale factor at 41.4° N is ~1.33.
- **Coverage warning at 75 % — chosen.** When under 75 % of an area's carriageway has a
  mapped speed limit, an insight says the speed figure rests on a minority of the streets
  (`LIMIT_COVERAGE_WARN` in `apps/kpis/insights.py`). Picked as "a clear majority"; the
  district sits at 89 %, so it fires only where mapping is genuinely thin. It changes no
  KPI value — only whether the sentence appears.
- **Denominators** are only ever length, building count or segment count. No socioeconomic
  quantity appears anywhere, as a KPI, a denominator or a control.
- **Palette.** Band pills are a single-hue blue ramp ordered by `lower_is_better`, never
  red/amber/green: a red card reads as "dangerous", the one claim these numbers cannot make.
  Map categories keep distinct hues; none is red.
- **Basemap.** OpenFreeMap `positron` tiles are drawn underneath as cartographic context
  only. No KPI reads them; every number, feature and colour comes from the Overture
  warehouse. Keyless; overridable with `VITE_BASEMAP_STYLE_URL`.
- **Release.** Overture `2026-08-19.0`, pinned in `backend/pipeline/release.py` and echoed
  in `meta.overture_release`; `meta.warehouse_build` identifies the build.
- **`access_restrictions` is not read.** Its dominant entry in the district is a one-way
  rule (`denied` + `heading = 'backward'`, no mode) that naive logic would read as "closed"
  and drop 80 % of residential streets. Any future KPI must filter on `when.mode` first.

## Rejected KPIs (numbers from `pipeline/recon.py`, re-run 2026-09-22)

| Candidate | Rejected because | The number that decided it |
|---|---|---|
| `lit_street_share` | Overture carries a sample of the district's lamps, concentrated where individual mappers surveyed; the KPI would measure mapping effort and a low reading would present as "dark street". | 236 lamps in 7.5 km² — 1 per 707 m of carriageway; 65 % of them in two 1-km cells, while a full cell with 58.9 km of road has 0. |
| `transit_stop_distance_p50` | No spatial variance: every polygon reads "excellent", so draw-and-recompute looks broken. | 100 % of 8,397 buildings within 300 m of a stop (p50 79 m, p90 144 m). |
| `land_use_mix` | An entropy over land-use polygons measures mapping coverage, not mix. | Land-use polygons cover 29.7 % of the district (2.23 of 7.51 km²), 61 % of that one class. |
| `green_share` | Duplicates the distance KPI's data with less variance across Eixample. | Green union 0.44 km² = 5.9 % of the district. |
| `junction_density` | Computable but says least to a safety reader; kept as the fallback. | 2,731 connectors of degree ≥ 3 (1,977 + 754) = 364 /km². |

## Overture coverage gaps found

- Lamps are `infrastructure` `subtype = 'transportation'`, `class = 'street_lamp'`, not
  `utility`; 236 in the district.
- Sidewalks: 1,741 `footway/sidewalk` segments (169.4 km) plus 1,283 `crosswalk` (21.5 km)
  against 1,883 carriageway segments — roughly half of a grid where every street has two
  sidewalks. See the pedestrian KPI.
- No `road` struct: `speed_limits`, `road_flags`, `access_restrictions` are top-level
  columns. `speed_limits` covers 88.8 % of carriageway km, 12.1 % of `service` segments.
- Building `height` on 796 of 8,397 buildings (9.5 %), `num_floors` on 4,227 (50.3 %).
- Water is 0.10 % of the district (pools and basins); no natural water in Eixample.
- `transit/stop_position` (391 rows) duplicates stops one-per-vehicle-position; never a stop.
