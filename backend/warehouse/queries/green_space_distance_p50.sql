-- green_space_distance_p50
--
-- Median straight-line distance (m) from a building centroid inside the area to the nearest
-- green space of at least 0.5 ha. The size floor and the 300 m band both come from WHO
-- Europe, "Urban green spaces: a brief for action" (2017); see NOTES.md.
--
--   value = median over buildings in area of ( min over targets of ST_Distance(building, target) )
--
-- CLIPPING RULE (CLAUDE.md §8): this is a nearest-neighbour KPI. The POPULATION is clipped —
-- only building centroids inside the area — but the TARGET set is the FULL green_spaces
-- table, including polygons outside the drawn polygon and outside the district (the
-- warehouse keeps them 1.5 km beyond the district bbox for exactly this reason). Clipping
-- the targets would make a small polygon with no park inside it return null; this query
-- returns the distance to the park next door instead.
--
-- sample_size = building centroids inside the area.
-- breakdown   = buildings by distance band (<= 300 m WHO, 300-600 m, > 600 m); feeds the
--               chart and colours buildings on the map.
-- context     = share of buildings within 300 m, number of qualifying targets searched.

WITH population AS (
    SELECT b.id, b.geom_m
    FROM buildings b
    WHERE ST_Intersects(b.geom_m, area_m())
),
targets AS (
    SELECT g.geom_m
    FROM green_spaces g
    WHERE g.is_who_size
),
nearest AS (
    SELECT p.id,
           (SELECT min(ST_Distance(p.geom_m, t.geom_m)) FROM targets t) AS d
    FROM population p
),
sums AS (
    SELECT count(*)                                      AS n,
           quantile_cont(d, 0.5)                         AS p50,
           count(*) FILTER (WHERE d <= 300)              AS n_300,
           count(*) FILTER (WHERE d > 300 AND d <= 600)  AS n_600,
           count(*) FILTER (WHERE d > 600)               AS n_far
    FROM nearest
)
SELECT p50                                                          AS value,
       n                                                            AS sample_size,
       [
           {'key': 'within_300', 'label': '≤ 300 m',   'value': CAST(n_300 AS DOUBLE)},
           {'key': 'within_600', 'label': '300–600 m', 'value': CAST(n_600 AS DOUBLE)},
           {'key': 'beyond_600', 'label': '> 600 m',   'value': CAST(n_far AS DOUBLE)}
       ]                                                            AS breakdown,
       [
           {'key': 'share_within_300', 'label': 'Buildings within 300 m',
            'value': CASE WHEN n > 0 THEN CAST(100.0 * n_300 / n AS DOUBLE) END, 'unit': '%'},
           {'key': 'targets', 'label': 'Green spaces ≥ 0.5 ha searched',
            'value': CAST((SELECT count(*) FROM targets) AS DOUBLE), 'unit': ''}
       ]                                                            AS context
FROM sums;
