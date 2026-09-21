-- street_tree_density
--
-- Mapped street trees per kilometre of carriageway inside the area.
--
--   value = count(tree points inside area) / clipped carriageway length (km)
--
-- Points are in or out; carriageway length is clipped with ST_Intersection.
--
-- Clipped length short-circuits to the precomputed length_m when the segment is entirely
-- inside the area (ST_CoveredBy): 3x faster on the whole district, identical result.
--
-- sample_size = carriageway segments touching the area (the denominator population).
-- breakdown   = NULL, deliberately: Overture tree points carry no species, size or canopy, so
--               there is no category to split by.
-- context     = trees counted, carriageway km.

WITH clipped AS (
    SELECT CASE WHEN ST_CoveredBy(s.geom_m, area_m()) THEN s.length_m
                ELSE ST_Length(ST_Intersection(s.geom_m, area_m())) END AS len_m
    FROM segments s
    WHERE s.is_carriageway
      AND ST_Intersects(s.geom_m, area_m())
),
road AS (
    SELECT coalesce(sum(len_m), 0) AS len_m,
           count(*)                AS n_segments
    FROM clipped
    WHERE len_m > 0   -- a segment touching the boundary at a point is not in the area
),
points AS (
    SELECT count(*) AS n_trees
    FROM trees t
    WHERE ST_Intersects(t.geom_m, area_m())
)
SELECT CASE WHEN road.len_m > 0 THEN points.n_trees / (road.len_m / 1000.0) END AS value,
       road.n_segments                                                          AS sample_size,
       NULL::STRUCT(key VARCHAR, label VARCHAR, value DOUBLE)[]                 AS breakdown,
       [
           {'key': 'trees', 'label': 'Trees in area',
            'value': CAST(points.n_trees AS DOUBLE), 'unit': ''},
           {'key': 'carriageway_km', 'label': 'Carriageway in area',
            'value': CAST(road.len_m / 1000 AS DOUBLE), 'unit': 'km'}
       ]                                                                        AS context
FROM road, points;
