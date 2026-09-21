# NOTES — KPI reference

> **Status: first draft (Phase 0, 2026-09-19).** The set is decided; the SQL is not written yet.
> Numbers quoted here are from [`docs/recon.md`](docs/recon.md) (Overture `2026-08-19.0`,
> l'Eixample, 7.508 km²). This file becomes the reviewer's reference table in Phase 7.

Every band boundary below either cites a source I have read (with the URL and the quoted
sentence) or is marked **chosen** with the reasoning. Nothing is cited from memory.

## The set

| # | Key | Type | Denominator | Why this denominator |
|---|---|---|---|---|
| 1 | `low_speed_street_share` | share (%) | carriageway km **with a mapped speed limit** | Dividing by all carriageway km would let the 11 % of segments with no mapped limit depress the value for mapping reasons, not street reasons. The coverage share is returned alongside the value. |
| 2 | `crossing_density` | density (per km) | carriageway km | Per km², a polygon drawn over a park scores badly for no meaningful reason. Crossings exist to cross carriageways, so carriageway length is the natural base. |
| 3 | `pedestrian_network_share` | share (%) | total network km (all `subtype='road'` classes) | Share of the whole mapped network that is pedestrian-only geometry. |
| 4 | `green_space_distance_p50` | distance (m) | building count (centroids) | The population is "homes"; Overture has no population, buildings are the legal proxy. |
| 5 | `street_tree_density` (stretch) | density (per km) | carriageway km | Street trees line streets; area would reward parks twice. |

**Carriageway** = `subtype = 'road'` and `class NOT IN ('footway', 'steps', 'path', 'cycleway', 'pedestrian')`.
**Total network** = every `subtype = 'road'` segment regardless of class. Rail (`subtype = 'rail'`) is never counted.

## Reference table

| KPI | What it measures | How it is computed (words) | Bands | Source | What it does **not** claim |
|---|---|---|---|---|---|
| `low_speed_street_share` | Share of carriageway length whose posted limit is ≤ 30 km/h | Clip carriageway segments to the area; sum length where the first `speed_limits` rule's `max_speed.value` ≤ 30 (unit km/h); divide by summed length of clipped carriageway that has any `speed_limits` rule. Also return `coverage` = mapped-limit km / all carriageway km. | < 40 % **Mostly 50**; 40–70 % **Mixed**; ≥ 70 % **Calmed** | **Threshold 30 km/h — citation:** Real Decreto 970/2020, de 10 de noviembre (BOE-A-2020-13969, published 11 Nov 2020, art. 50 in force six months later). New art. 50.1 of the Reglamento General de Circulación sets urban limits of 20 km/h on single-platform streets, **30 km/h on roads with one lane per direction**, 50 km/h with two or more lanes per direction. https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969 . **Band boundaries 40/70 — chosen:** the district reads 50.7 % overall; bands are placed so a superblock interior and a through-route corridor land in different bands. | Posted limit, not observed speed. Segments without a mapped limit (11 % of carriageway km in the district; 88 % of `service`) are **excluded from both numerator and denominator, not assumed fast**. Says nothing about enforcement, crashes or lane count. |
| `crossing_density` | Pedestrian crossings per km of carriageway | Count `infrastructure` points with `class = 'crossing'` inside the area (a point is in or out, no clipping); divide by clipped carriageway km. | < 10 **Sparse**; 10–20 **Moderate**; ≥ 20 **Dense** | **Chosen.** No standard I could verify prescribes crossings per km. District mean is 22.6/km; bands are set at half and roughly the mean so that blocks with fewer crossings than the district norm read as such. | A crossing point carries no quality: signalised, raised, marked, lit or not. High density does not mean safe crossing; low density in a pedestrianised area is meaningless (there is no carriageway to cross). |
| `pedestrian_network_share` | Share of mapped network length that is pedestrian-only | Clip all `subtype='road'` segments; numerator = length where `class IN ('footway', 'pedestrian', 'steps', 'path')`; denominator = all clipped length. | < 30 % **Car-dominated**; 30–60 % **Mixed**; ≥ 60 % **Walking-first** | **Chosen.** District reads 52 %. Bands bracket the district figure so pedestrianised streets and superblocks (higher) and through-route blocks (lower) separate. | **Comparability caveat:** Overture (from OSM) maps sidewalks as separate `footway/sidewalk` geometry in Barcelona (1,741 sidewalk segments in the district). That inflates pedestrian km relative to a city where sidewalks are attributes of the road, so this number cannot be compared across cities with different mapping conventions. It does not measure sidewalk width, quality or continuity. |
| `green_space_distance_p50` | Median straight-line distance from a building to the nearest mapped green space of ≥ 0.5 ha | Population = centroids of buildings intersecting the area. Targets = `land_use` polygons with green subtypes (`park`, `horticulture`, `managed`, `recreation`, `agriculture`) **and area ≥ 0.5 ha** (the WHO size floor), taken from the district plus a 1.5 km margin so edge buildings see greens outside the district. Distance = `ST_Distance` in EPSG:25831 to the nearest target; report the median. **Buildings with no target within the extract margin are not excluded and not clamped: the extract carries every ≥ 0.5 ha green within 1.5 km of the district bbox, and Phase 3 asserts that no building's nearest target lies beyond that margin (if one does, the number is reported as `> 1500 m` and flagged in `meta`).** | ≤ 300 m **Within WHO rule of thumb**; 300–600 m **Beyond**; > 600 m **Far** | **Threshold 300 m and 0.5 ha — citation:** WHO Regional Office for Europe, *Urban green spaces: a brief for action* (2017), p. 11: "As a rule of thumb, urban residents should be able to access public green spaces of at least 0.5–1 hectare within 300 metres' linear distance (around 5 minutes' walk) of their homes." https://www.who.int/europe/publications/i/item/9789289052498 . **600 m boundary — chosen:** double the WHO distance; nothing in the brief prescribes a second band. | Straight-line, not walking distance; a park across a railway reads as near. Only polygons Overture carries — Eixample's interior courtyard gardens are largely unmapped, and small pocket greens under 0.5 ha are deliberately ignored. Building centroids are not people. |
| `street_tree_density` | Mapped street trees per km of carriageway | Count `land` points with `class = 'tree'` inside the area; divide by clipped carriageway km. | < 20 **Sparse**; 20–50 **Moderate**; ≥ 50 **Dense** | **Chosen.** District reads 53/km with every full 1-km cell between 752 and 2,001 trees. Bands sit at the district mean and at less than half of it. | Tree points are a shade/greenness proxy, not a safety measure. Canopy size, species and health are unknown; a sapling counts as a plane tree. Mapping is OSM-derived and can be uneven outside the district. |

## Rules that apply to every KPI

- **Clipping:** linear features contribute the length of their part inside the drawn area
  (`ST_Intersection`), not all-or-nothing. Points are in or out. Polygons used as targets
  (green spaces) are never clipped — a park half outside the area is still a park.
- **Projection:** all metres in EPSG:25831 (ETRS89 / UTM 31N), `always_xy := true` on every
  transform (CLAUDE.md rule 9). Never EPSG:3857 — its scale factor at 41.4° N is ~1.33.
- **Denominators** are only ever length, area, building count or segment count (CLAUDE.md
  rule 2). No socioeconomic quantity appears anywhere.
- **Empty is a state:** `sample_size = 0` returns `value: null`, not an error and not zero.
- **Palette, deliberately not a traffic light.** Band pills are never red/amber/green: a red
  card reads as "this place is dangerous", exactly the claim these numbers cannot support
  (CLAUDE.md rule 4). Bands are coloured with a single-hue sequential scale and
  `lower_is_better` only *orders* them. Map categories (speed bands, segment classes) are
  categorical and keep distinct hues, but none of them is red either.
- **The basemap is not a data source.** The map draws OpenFreeMap's `positron` vector tiles
  underneath as cartographic context (streets and labels to orient by). No KPI reads it,
  nothing is joined to it, and every number, feature and colour on screen comes from the
  Overture warehouse. It is keyless and overridable (`VITE_BASEMAP_STYLE_URL`).
- **Areas partly or fully outside the district.** The warehouse holds features for the
  district only, so a polygon crossing the boundary is measured on its inside part. The
  response says so: `area.district_overlap_share` (area of intersection with the district
  over area of the polygon, both in EPSG:25831) and an insight sentence. A polygon entirely
  outside is a 200 with `sample_size = 0`, not an error.
- **`access_restrictions` is not read by any KPI.** Phase 0 found that its dominant entry is a
  one-way rule (`denied` + `heading = 'backward'`, no mode) which naive logic would read as
  "closed" and thereby remove 80 % of residential streets. The chosen KPIs are class-based
  and never touch the column; if a future KPI does, it must filter on `when.mode` and treat
  heading-only rules as one-way, not as denials.

## Rejected KPIs (kept as evidence, quoted in the walkthrough)

| Candidate | Rejected because | The number |
|---|---|---|
| `lit_street_share` | **Coverage.** Overture carries a sample of the district's lamps, concentrated where individual mappers surveyed. The KPI would measure mapping effort, not lighting, and a low reading would present as "dark street". | 236 lamps in 7.5 km²; 1 per 707 m of street; 65 % in two 1-km cells; a full cell with 59 km of road has 0. Lamps are `subtype='transportation'`, not `utility`. |
| `transit_stop_distance_p50` | **Saturation.** Cleanest data in the extract, but no spatial variance: every polygon reads "excellent", which makes draw-and-recompute look broken. | 287 bus stops + 27 subway stations; building p50 = 79 m, p90 = 144 m; **100 %** of 8,397 buildings within 300 m. |
| `land_use_mix` | Land-use polygons cover 30 % of the district, 61 % of that one class. An entropy over it measures mapping coverage. | 2.23 km² mapped of 7.51; residential 1.37 km². |
| `green_share` | Replaced by the distance KPI: varies less across Eixample and duplicates its data. | Green union 0.44 km² = 5.9 %; water 0.1 %. |
| `junction_density` | Computable (GREEN) but says least to a safety reader; kept as fallback. | 2,731 connectors with degree ≥ 3 = 364/km². |

## Overture coverage gaps found (Phase 0)

- No `utility/street_lamp`; lamps are `transportation/street_lamp` and sparse (above).
- No `road` struct; `speed_limits`, `road_flags`, `access_restrictions`, `road_surface` are
  top-level columns. `speed_limits` is populated on 89 % of carriageway km.
- Building `height` on 9.5 % of buildings; `num_floors` on 50 %.
- Water: 0.1 % of the district (pools and basins); no natural water in Eixample.
- `transit/stop_position` (391) duplicates bus stops and stations one-per-vehicle-position and
  must never be counted as a stop.
