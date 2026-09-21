-- layer: streets_speed  (kpi: low_speed_street_share)
--
-- Carriageway segments touching the area, clipped to it in EPSG:25831 and served back in
-- EPSG:4326 so the map shows exactly the geometry the KPI measured. `category` is the
-- posted-speed band key used by the KPI breakdown, so a click on the chart can filter the map.

WITH clipped AS (
    SELECT s.id, s.name, s.class, s.max_speed_kmh,
           -- ST_CollectionExtract(…, 2) keeps only the line parts: a segment that merely
           -- touches the area boundary intersects it in a point, which is not a street.
           CASE WHEN ST_CoveredBy(s.geom_m, area_m()) THEN s.geom_m
                ELSE ST_CollectionExtract(ST_Intersection(s.geom_m, area_m()), 2) END AS geom_m
    FROM segments s
    WHERE s.is_carriageway
      AND ST_Intersects(s.geom_m, area_m())
)
SELECT to_json({
    'type': 'Feature',
    'id': id,
    'geometry': ST_AsGeoJSON(ST_ReducePrecision(
        ST_Transform(geom_m, 'EPSG:25831', 'EPSG:4326', always_xy := true), 0.000001))::JSON,
    'properties': {
        'name': name,
        'class': class,
        'max_speed_kmh': max_speed_kmh,
        'length_m': round(ST_Length(geom_m), 1),
        'category': CASE WHEN max_speed_kmh IS NULL THEN 'none'
                         WHEN max_speed_kmh <= 20 THEN 'le20'
                         WHEN max_speed_kmh <= 30 THEN 'le30'
                         WHEN max_speed_kmh <= 50 THEN 'le50'
                         ELSE 'gt50' END
    }
}) AS feature
FROM clipped
WHERE NOT ST_IsEmpty(geom_m);
