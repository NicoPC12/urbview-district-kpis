-- layer: buildings_green  (kpi: green_space_distance_p50)
--
-- Building centroids inside the area with their distance to the nearest green space of at
-- least 0.5 ha. CLIPPING RULE (CLAUDE.md §8): population clipped, targets searched in the full
-- warehouse — same as the KPI query. `category` is the distance band of the breakdown.

WITH population AS (
    SELECT b.id, b.geom, b.geom_m
    FROM buildings b
    WHERE ST_Intersects(b.geom_m, area_m())
),
targets AS (
    SELECT g.id, g.geom_m FROM green_spaces g
    WHERE g.is_who_size AND (g.subtype, g.class) IN (SELECT * FROM public_green_classes)
),
nearest AS (
    SELECT p.id, p.geom,
           (SELECT min(ST_Distance(p.geom_m, t.geom_m)) FROM targets t) AS distance_m
    FROM population p
)
SELECT to_json({
    'type': 'Feature',
    'id': id,
    'geometry': ST_AsGeoJSON(ST_ReducePrecision(geom, 0.00001))::JSON,
    'properties': {
        'category': CASE WHEN distance_m <= 300 THEN 'within_300'
                         WHEN distance_m <= 600 THEN 'within_600'
                         ELSE 'beyond_600' END,
        'distance_m': round(distance_m, 1)
    }
}) AS feature
FROM nearest;
