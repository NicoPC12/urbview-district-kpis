-- layer: streets_class  (kpi: pedestrian_network_share)
--
-- Every road-subtype segment touching the area, clipped in EPSG:25831 and served in EPSG:4326.
-- `category` is the segment class, matching the KPI breakdown keys.

WITH clipped AS (
    SELECT s.id, s.name, s.class,
           -- ST_CollectionExtract(…, 2) keeps only the line parts: a segment that merely
           -- touches the area boundary intersects it in a point, which is not a street.
           CASE WHEN ST_CoveredBy(s.geom_m, area_m()) THEN s.geom_m
                ELSE ST_CollectionExtract(ST_Intersection(s.geom_m, area_m()), 2) END AS geom_m
    FROM segments s
    WHERE ST_Intersects(s.geom_m, area_m())
)
SELECT to_json({
    'type': 'Feature',
    'id': id,
    'geometry': ST_AsGeoJSON(ST_ReducePrecision(
        ST_Transform(geom_m, 'EPSG:25831', 'EPSG:4326', always_xy := true), 0.00001))::JSON,
    'properties': json_merge_patch('{}', to_json({
        'category': class,
        'name': name,
        'length_m': round(ST_Length(geom_m), 1)
    }))
}) AS feature
FROM clipped
WHERE NOT ST_IsEmpty(geom_m);
