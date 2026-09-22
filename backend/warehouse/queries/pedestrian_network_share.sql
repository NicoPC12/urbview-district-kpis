-- pedestrian_network_share
--
-- Share (%) of the street network length inside the area that is pedestrian-only geometry
-- (pedestrian streets, footways, steps, paths) — EXCLUDING sidewalk and crosswalk geometry.
--
--   value = 100 * clipped length(pedestrian classes, not sidewalk/crosswalk)
--               / clipped length(all road-subtype classes, not sidewalk/crosswalk)
--
-- Why sidewalks are out (NOTES.md, pipeline/derive_bands.py): Overture maps Barcelona's
-- sidewalks as separate `footway/sidewalk` lines, but only about half of them — the ratio of
-- mapped sidewalk km to carriageway km varies from 0.7 to 1.5 across 250 m cells. With them
-- in, the KPI measured OSM sidewalk coverage, not the street. Without them it measures street
-- space given over to walking, which is also what a planner can change.
--
-- Both sides are clipped with ST_Intersection. Cycleways and carriageways are in the
-- denominator only.
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
      AND coalesce(s.subclass, '') NOT IN ('sidewalk', 'crosswalk')
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
