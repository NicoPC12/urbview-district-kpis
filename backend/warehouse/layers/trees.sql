-- layer: trees  (kpi: street_tree_density)
--
-- Tree points inside the area. One category: Overture tree points carry no attributes.

SELECT to_json({
    'type': 'Feature',
    'id': t.id,
    'geometry': ST_AsGeoJSON(ST_ReducePrecision(t.geom, 0.000001))::JSON,
    'properties': {'category': 'tree'}
}) AS feature
FROM trees t
WHERE ST_Intersects(t.geom_m, area_m());
