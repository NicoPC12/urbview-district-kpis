# Derived bands — 156 cells of 250 m over the district

Overture 2026-08-19.0. 250 m grid in EPSG:25831 clipped to the district; each KPI computed per cell with the production SQL; cells with less than 0.5 km of denominator dropped (chosen); cutoffs = P33 and P67 of the per-cell values, rounded to two significant figures. Regenerate with `make derive-bands`.

| KPI | cells kept | dropped (< 0.5 km) | min | P33 | median | P67 | max | cutoffs |
|---|---|---|---|---|---|---|---|---|
| `low_speed_street_share` | 125 | 31 | 0.0 | 41.6 | 50.6 | 60.2 | 100.0 | **42 / 60** |
| `crossing_density` | 129 | 27 | 5.9 | 19.5 | 22.8 | 26.2 | 38.8 | **19 / 26** |
| `pedestrian_network_share` | 136 | 20 | 0.0 | 13.8 | 18.7 | 23.9 | 70.7 | **14 / 24** |
| `street_tree_density` | 129 | 27 | 0.0 | 20.2 | 43.8 | 69.0 | 358.2 | **20 / 69** |

# Sidewalk mapping per cell — sidewalk km / carriageway km

cells: 129 · min 0.00 · P10 0.68 · P25 0.89 · median 1.09 · P75 1.39 · P90 1.54 · max 1.85 · cells with ratio < 0.5: 5 · cells with ratio > 1.5: 17
