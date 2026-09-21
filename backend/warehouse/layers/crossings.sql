-- layer: crossings  (kpi: crossing_density)
--
-- Crossing points inside the area. One category: a crossing carries no attributes in Overture.

SELECT to_json({
    'type': 'Feature',
    'id': c.id,
    'geometry': ST_AsGeoJSON(ST_ReducePrecision(c.geom, 0.000001))::JSON,
    'properties': {'category': 'crossing'}
}) AS feature
FROM crossings c
WHERE ST_Intersects(c.geom_m, area_m());
