/**
 * Hand-sized KPI responses typed against the generated schema, so a contract change that
 * breaks the UI also breaks the fixture at compile time.
 */

import type { District, KpiResponse } from '@/api/schema.gen';

const SQUARE = [
  [2.16, 41.39],
  [2.17, 41.39],
  [2.17, 41.397],
  [2.16, 41.397],
  [2.16, 41.39],
];

export const district: District = {
  slug: 'eixample',
  name: 'Eixample',
  km2: 7.51,
  bbox: [2.142, 41.375, 2.187, 41.412],
  geometry: { type: 'Polygon', coordinates: [SQUARE] },
};

/** The whole district: every KPI populated, two features per layer. */
export const districtResponse: KpiResponse = {
  area: { name: "l'Eixample", km2: 7.51, source: 'district', district_overlap_share: 1 },
  kpis: [
    {
      key: 'low_speed_street_share',
      label: 'Carriageway limited to 30 km/h or less',
      value: 50.7,
      unit: '%',
      band: 'Mixed',
      definition: 'Share of carriageway length with a posted limit of 30 km/h or lower.',
      not_claim: 'A posted limit, not an observed speed.',
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'citation',
        label: 'Real Decreto 970/2020',
        url: 'https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969',
      },
      bands: [
        { label: 'Mostly 50', max: 40 },
        { label: 'Mixed', max: 70 },
        { label: 'Calmed', max: null },
      ],
      sample_size: 1435,
      breakdown: [
        { key: 'le30', label: '30 km/h or less', value: 72.4 },
        { key: 'le50', label: '31–50 km/h', value: 70.3 },
        { key: 'none', label: 'No mapped limit', value: 17.6 },
      ],
      context: [
        { key: 'limit_coverage', label: 'Carriageway with a mapped limit', value: 89, unit: '%' },
        { key: 'mapped_km', label: 'Carriageway with a mapped limit', value: 142.7, unit: 'km' },
      ],
    },
    {
      key: 'crossing_density',
      label: 'Pedestrian crossings per km of carriageway',
      value: 22.6,
      unit: '/km',
      band: 'Dense',
      definition: 'Mapped crossing points per kilometre of carriageway.',
      not_claim: 'A crossing point carries no quality.',
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: { kind: 'chosen', label: 'Chosen', url: null, note: 'Half the district mean.' },
      bands: [
        { label: 'Sparse', max: 10 },
        { label: 'Moderate', max: 20 },
        { label: 'Dense', max: null },
      ],
      sample_size: 1754,
      breakdown_note: 'No breakdown: Overture carries no attributes on a crossing point.',
      context: [{ key: 'crossings', label: 'Crossings', value: 3624, unit: '' }],
    },
    {
      key: 'green_space_distance_p50',
      label: 'Median distance to a green space of at least 0.5 ha',
      value: 362,
      unit: 'm',
      band: 'Beyond',
      definition: 'Median straight-line distance from a building centroid to the nearest park.',
      not_claim: 'Straight-line, not walking distance.',
      denominator: 'building_count',
      lower_is_better: true,
      source: { kind: 'citation', label: 'WHO Europe 2017', url: 'https://www.who.int/' },
      bands: [
        { label: 'Within WHO rule of thumb', max: 300 },
        { label: 'Beyond', max: 600 },
        { label: 'Far', max: null },
      ],
      sample_size: 8397,
      breakdown: [
        { key: 'within_300', label: 'Within 300 m', value: 3428 },
        { key: 'within_600', label: '300–600 m', value: 3900 },
        { key: 'beyond_600', label: 'Beyond 600 m', value: 1069 },
      ],
      context: [{ key: 'share_within_300', label: 'Within 300 m', value: 40.8, unit: '%' }],
    },
  ],
  insights: ['51% of the 142.7 km of carriageway with a mapped limit is 30 km/h or less.'],
  legend: {
    type: 'categorical',
    items: [
      {
        kpi_key: 'low_speed_street_share',
        key: 'le30',
        label: '30 km/h or less',
        color: '#0f766e',
      },
      { kpi_key: 'low_speed_street_share', key: 'le50', label: '31–50 km/h', color: '#b45309' },
      {
        kpi_key: 'low_speed_street_share',
        key: 'none',
        label: 'No mapped limit',
        color: '#94a3b8',
      },
      { kpi_key: 'crossing_density', key: 'crossing', label: 'crossing', color: '#1d4ed8' },
      {
        kpi_key: 'green_space_distance_p50',
        key: 'within_300',
        label: 'Within 300 m',
        color: '#15803d',
      },
      {
        kpi_key: 'green_space_distance_p50',
        key: 'within_600',
        label: '300–600 m',
        color: '#b45309',
      },
      {
        kpi_key: 'green_space_distance_p50',
        key: 'green_space',
        label: 'green space',
        color: '#22c55e',
      },
    ],
  },
  layers: {
    vectors: [
      {
        id: 'streets_speed',
        kpi_key: 'low_speed_street_share',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: 'seg-a',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.16, 41.39],
                  [2.162, 41.39],
                ],
              },
              properties: { category: 'le30', name: "Carrer d'Aragó", length_m: 182 },
            },
            {
              type: 'Feature',
              id: 'seg-b',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.16, 41.391],
                  [2.163, 41.391],
                ],
              },
              properties: { category: 'le50', length_m: 250 },
            },
          ],
        },
      },
      {
        id: 'crossings',
        kpi_key: 'crossing_density',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: 'cross-a',
              geometry: { type: 'Point', coordinates: [2.161, 41.39] },
              properties: { category: 'crossing' },
            },
          ],
        },
      },
      {
        id: 'buildings_green',
        kpi_key: 'green_space_distance_p50',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: 'bld-a',
              geometry: { type: 'Point', coordinates: [2.161, 41.392] },
              properties: { category: 'within_600', distance_m: 412 },
            },
            {
              type: 'Feature',
              id: 'bld-b',
              geometry: { type: 'Point', coordinates: [2.162, 41.392] },
              properties: { category: 'within_300', distance_m: 120 },
            },
          ],
        },
      },
    ],
  },
  meta: {
    computed_ms: 2100,
    cached: false,
    overture_release: '2026-08-19.0',
    warehouse_build: 'efebeffb8727',
    timings_ms: { low_speed_street_share: 90.9 },
  },
};

/** A drawn polygon with different numbers, half inside the district. */
export const drawnResponse: KpiResponse = {
  ...districtResponse,
  area: { name: 'Drawn area', km2: 0.74, source: 'drawn', district_overlap_share: 0.57 },
  kpis: districtResponse.kpis.map((kpi) =>
    kpi.key === 'low_speed_street_share'
      ? { ...kpi, value: 88.2, band: 'Calmed', sample_size: 61 }
      : kpi.key === 'crossing_density'
        ? { ...kpi, value: 9.1, band: 'Sparse', sample_size: 61 }
        : { ...kpi, value: 210, band: 'Within WHO rule of thumb', sample_size: 447 },
  ),
  insights: ['88% of the 3.1 km of carriageway with a mapped limit is 30 km/h or less.'],
};

/** A polygon over the sea: every KPI empty. */
export const emptyResponse: KpiResponse = {
  ...districtResponse,
  area: { name: 'Drawn area', km2: 1.46, source: 'drawn', district_overlap_share: 0 },
  kpis: districtResponse.kpis.map((kpi) => ({
    ...kpi,
    breakdown: undefined,
    value: null,
    band: null,
    sample_size: 0,
  })),
  insights: ['The 1.46 km² area contains none of the features the KPIs measure.'],
  layers: {
    vectors: districtResponse.layers.vectors.map((layer) => ({
      ...layer,
      data: { type: 'FeatureCollection', features: [] },
    })),
  },
};
