-- layer: green_spaces  (kpi: green_space_distance_p50)
--
-- The green spaces (≥ 0.5 ha) that are the nearest target for at least one building in the
-- area — usually including parks outside the drawn polygon, which is the point: the map shows
-- what the distance KPI measured to.

WITH population AS (
    SELECT b.geom_m FROM buildings b WHERE ST_Intersects(b.geom_m, area_m())
),
targets AS (
    SELECT g.id, g.geom_m FROM green_spaces g WHERE g.is_who_size
),
used AS (
    SELECT DISTINCT
           (SELECT t.id FROM targets t ORDER BY ST_Distance(p.geom_m, t.geom_m) LIMIT 1) AS id
    FROM population p
)
SELECT to_json({
    'type': 'Feature',
    'id': g.id,
    'geometry': ST_AsGeoJSON(ST_ReducePrecision(g.geom, 0.000001))::JSON,
    'properties': {
        'name': g.name,
        'class': g.class,
        'area_ha': round(g.area_m2 / 10000, 2),
        'category': 'green_space'
    }
}) AS feature
FROM green_spaces g
WHERE g.id IN (SELECT id FROM used);
