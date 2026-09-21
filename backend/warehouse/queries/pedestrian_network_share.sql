-- pedestrian_network_share
--
-- Share (%) of the mapped network length inside the area that is pedestrian-only geometry
-- (footway, pedestrian, steps, path).
--
--   value = 100 * clipped length(pedestrian classes) / clipped length(all road-subtype classes)
--
-- Both sides are clipped with ST_Intersection. Cycleways and carriageways are in the
-- denominator only. Comparability caveat (NOTES.md): sidewalks are separate geometry here,
-- which inflates pedestrian km relative to cities that map sidewalks as road attributes.
--
-- Clipped length short-circuits to the precomputed length_m when the segment is entirely
-- inside the area (ST_CoveredBy): 3x faster on the whole district, identical result.
--
-- sample_size = segments touching the area.
-- breakdown   = clipped km by segment class, largest first (feeds the chart and the map filter).
-- context     = pedestrian km, total network km.

WITH clipped AS (
    SELECT s.class,
           s.is_pedestrian,
           CASE WHEN ST_CoveredBy(s.geom_m, area_m()) THEN s.length_m
                ELSE ST_Length(ST_Intersection(s.geom_m, area_m())) END AS len_m
    FROM segments s
    WHERE ST_Intersects(s.geom_m, area_m())
),
by_class AS (
    SELECT class, sum(len_m) AS len_m
    FROM clipped
    WHERE len_m > 0
    GROUP BY class
),
sums AS (
    SELECT coalesce(sum(len_m), 0)                               AS all_m,
           coalesce(sum(len_m) FILTER (WHERE is_pedestrian), 0)  AS ped_m,
           count(*)                                              AS n
    FROM clipped
    WHERE len_m > 0   -- a segment touching the boundary at a point is not in the area
)
SELECT CASE WHEN all_m > 0 THEN 100.0 * ped_m / all_m END           AS value,
       n                                                            AS sample_size,
       -- Longest class first, name as tie-break: the order is part of the contract (the
       -- chart and the cache compare it), so it must not depend on aggregation threads.
       (SELECT list({'key': class, 'label': class, 'value': CAST(len_m / 1000 AS DOUBLE)}
                    ORDER BY len_m DESC, class)
        FROM by_class)                                              AS breakdown,
       [
           {'key': 'pedestrian_km', 'label': 'Pedestrian-only network',
            'value': CAST(ped_m / 1000 AS DOUBLE), 'unit': 'km'},
           {'key': 'network_km', 'label': 'All mapped network',
            'value': CAST(all_m / 1000 AS DOUBLE), 'unit': 'km'}
       ]                                                            AS context
FROM sums;
