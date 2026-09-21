-- low_speed_street_share
--
-- Share (%) of carriageway length inside the area whose posted limit is 30 km/h or lower,
-- over the carriageway length inside the area that has a mapped limit at all.
--
--   value = 100 * length(limit <= 30) / length(has a mapped limit)
--
-- Population is clipped: each carriageway segment contributes only the part of it inside the
-- area (ST_Intersection), numerator and denominator alike. Segments without a mapped limit
-- are excluded from both, not assumed fast; their share is reported as context so the reader
-- can see how much of the carriageway the value rests on.
--
-- Clipped length short-circuits to the precomputed length_m when the segment is entirely
-- inside the area (ST_CoveredBy): 3x faster on the whole district, identical result.
--
-- sample_size = carriageway segments with a mapped limit touching the area.
-- breakdown   = clipped km by posted-speed band (feeds the chart and the map filter).
-- context     = limit coverage (%), carriageway km, carriageway km with a limit.

WITH clipped AS (
    SELECT s.id,
           s.max_speed_kmh,
           s.has_speed_limit,
           CASE WHEN ST_CoveredBy(s.geom_m, area_m()) THEN s.length_m
                ELSE ST_Length(ST_Intersection(s.geom_m, area_m())) END AS len_m
    FROM segments s
    WHERE s.is_carriageway
      AND ST_Intersects(s.geom_m, area_m())
),
sums AS (
    SELECT coalesce(sum(len_m), 0)                                                AS all_m,
           coalesce(sum(len_m) FILTER (WHERE has_speed_limit), 0)                 AS mapped_m,
           coalesce(sum(len_m) FILTER (WHERE max_speed_kmh <= 30), 0)             AS low_m,
           count(*) FILTER (WHERE has_speed_limit)                                AS n_mapped,
           coalesce(sum(len_m) FILTER (WHERE max_speed_kmh <= 20), 0)             AS band_20,
           coalesce(sum(len_m) FILTER (WHERE max_speed_kmh BETWEEN 21 AND 30), 0) AS band_30,
           coalesce(sum(len_m) FILTER (WHERE max_speed_kmh BETWEEN 31 AND 50), 0) AS band_50,
           coalesce(sum(len_m) FILTER (WHERE max_speed_kmh > 50), 0)              AS band_fast,
           coalesce(sum(len_m) FILTER (WHERE NOT has_speed_limit), 0)             AS band_none
    FROM clipped
    WHERE len_m > 0   -- a segment touching the boundary at a point is not in the area
)
SELECT CASE WHEN mapped_m > 0 THEN 100.0 * low_m / mapped_m END AS value,
       n_mapped                                                  AS sample_size,
       [
           {'key': 'le20', 'label': '≤ 20 km/h',       'value': CAST(band_20   / 1000 AS DOUBLE)},
           {'key': 'le30', 'label': '21–30 km/h',      'value': CAST(band_30   / 1000 AS DOUBLE)},
           {'key': 'le50', 'label': '31–50 km/h',      'value': CAST(band_50   / 1000 AS DOUBLE)},
           {'key': 'gt50', 'label': '> 50 km/h',       'value': CAST(band_fast / 1000 AS DOUBLE)},
           {'key': 'none', 'label': 'No mapped limit', 'value': CAST(band_none / 1000 AS DOUBLE)}
       ]                                                         AS breakdown,
       [
           {'key': 'limit_coverage', 'label': 'Carriageway with a mapped limit',
            'value': CASE WHEN all_m > 0 THEN CAST(100.0 * mapped_m / all_m AS DOUBLE) END,
            'unit': '%'},
           {'key': 'carriageway_km', 'label': 'Carriageway in area',
            'value': CAST(all_m / 1000 AS DOUBLE), 'unit': 'km'},
           {'key': 'mapped_km', 'label': 'Carriageway with a mapped limit',
            'value': CAST(mapped_m / 1000 AS DOUBLE), 'unit': 'km'}
       ]                                                         AS context
FROM sums;
