/**
 * Real API responses, captured on 2026-09-25 from a warehouse built at Overture
 * 2026-08-19.0, so every number a test asserts also exists in the running app.
 *
 * Regenerate by POSTing to `/api/v1/kpis` and trimming each layer to two features:
 *   district — {"district": "eixample"}
 *   area A   — the Sant Antoni superblock polygon from docs/reference-areas/
 * `meta.computed_ms` and `meta.timings_ms` are pinned (per-run noise), and
 * `emptyResponse` is derived from the district response by nulling its values — the
 * one synthetic case here.
 */

import type { District, KpiResponse } from '@/api/schema.gen';

/** The district catalogue entry, outline trimmed to six positions. */
export const district: District = {
  slug: 'eixample',
  name: 'Eixample',
  km2: 7.508075837437012,
  bbox: [2.1420218, 41.3749101, 2.1867757, 41.4120331],
  geometry: {
    type: 'Polygon',
    coordinates: [
      [
        [2.16352, 41.37491],
        [2.16346, 41.37491],
        [2.16343, 41.37491],
        [2.16339, 41.37491],
        [2.16333, 41.37491],
        [2.16352, 41.37491],
      ],
    ],
  },
};

/** The whole district. */
export const districtResponse: KpiResponse = {
  area: {
    name: "l'Eixample",
    km2: 7.508075837437012,
    source: 'district',
    district_overlap_share: 1.0,
  },
  kpis: [
    {
      key: 'low_speed_street_share',
      label: 'Carriageway limited to 30 km/h or less',
      value: 50.732929603350435,
      unit: '%',
      band: 'Middle third',
      definition:
        'Share of carriageway length inside the area whose posted speed limit is 30 km/h or lower, over the carriageway length that has a mapped limit at all.',
      not_claim:
        "A posted limit, not an observed speed. Carriageway without a mapped limit is excluded from both numerator and denominator, not assumed fast; the share excluded is shown alongside. Says nothing about enforcement, crashes or lane count. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label:
          "30 km/h: Real Decreto 970/2020 (BOE-A-2020-13969), art. 50 RGC; bands derived from Eixample's 250 m cells (P33 / P67)",
        url: 'https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969',
        note: "The 30 km/h threshold is the statutory urban limit for roads with one lane per direction since 11 May 2021 (art. 50.1 RGC: 20 km/h single-platform streets, 30 km/h one lane per direction, 50 km/h two or more). Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 42.0,
        },
        {
          label: 'Middle third',
          max: 60.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 1435,
      breakdown: [
        {
          key: 'le20',
          label: '≤ 20 km/h',
          value: 17.457091396066435,
        },
        {
          key: 'le30',
          label: '21–30 km/h',
          value: 54.94784620260583,
        },
        {
          key: 'le50',
          label: '31–50 km/h',
          value: 70.31289510833254,
        },
        {
          key: 'gt50',
          label: '> 50 km/h',
          value: 0.0,
        },
        {
          key: 'none',
          label: 'No mapped limit',
          value: 17.61888965797578,
        },
      ],
      context: [
        {
          key: 'limit_coverage',
          label: 'Carriageway with a mapped limit',
          value: 89.01131980366338,
          unit: '%',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 160.3367223649808,
          unit: 'km',
        },
        {
          key: 'mapped_km',
          label: 'Carriageway with a mapped limit',
          value: 142.71783270700493,
          unit: 'km',
        },
      ],
    },
    {
      key: 'crossing_density',
      label: 'Pedestrian crossings per km of carriageway',
      value: 22.602432845986122,
      unit: '/km',
      band: 'Middle third',
      definition:
        'Mapped pedestrian crossing points inside the area per kilometre of carriageway inside the area.',
      not_claim:
        "A crossing point carries no quality: signalised, raised, marked or lit are not known. High density does not mean safe crossing, and a pedestrianised area with no carriageway has nothing to cross and reads as no data, not as zero. In shared-space or living streets, fewer marked crossings can mean the whole street has become crossable; a low reading there is not a deficit. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "No standard I could verify prescribes crossings per kilometre. Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 19.0,
        },
        {
          label: 'Middle third',
          max: 26.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 1754,
      breakdown_note:
        'No breakdown: Overture carries no attributes on a crossing point to split by.',
      context: [
        {
          key: 'crossings',
          label: 'Crossings in area',
          value: 3624.0,
          unit: '',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 160.3367223649808,
          unit: 'km',
        },
      ],
    },
    {
      key: 'pedestrian_network_share',
      label: 'Street network that is pedestrian-only (sidewalks excluded)',
      value: 20.603120648332535,
      unit: '%',
      band: 'Middle third',
      definition:
        'Share of the mapped street network length inside the area that is pedestrian-only geometry — pedestrian streets, footways, steps and paths — with sidewalk and crosswalk geometry excluded from both sides.',
      not_claim:
        "Street space given over to walking, not sidewalk provision: sidewalks and crosswalks are deliberately excluded because their mapping is incomplete. Says nothing about sidewalk width, quality or continuity. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'network_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "Sidewalks are excluded because Overture maps only about half of Barcelona's sidewalks as separate lines (mapped sidewalk km per carriageway km ranges from 0.7 to 1.5 across cells, median 1.1): with them in, the KPI measured mapping coverage, not the street. Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 14.0,
        },
        {
          label: 'Middle third',
          max: 24.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 3562,
      breakdown: [
        {
          key: 'cycleway',
          label: 'cycleway',
          value: 69.07026344691354,
        },
        {
          key: 'residential',
          label: 'residential',
          value: 52.062987376492416,
        },
        {
          key: 'footway',
          label: 'footway',
          value: 50.56478641060942,
        },
        {
          key: 'secondary',
          label: 'secondary',
          value: 35.89141787649783,
        },
        {
          key: 'tertiary',
          label: 'tertiary',
          value: 26.999600073567564,
        },
        {
          key: 'living_street',
          label: 'living_street',
          value: 14.645769588137775,
        },
        {
          key: 'primary',
          label: 'primary',
          value: 13.838696471138078,
        },
        {
          key: 'service',
          label: 'service',
          value: 12.79024303669529,
        },
        {
          key: 'pedestrian',
          label: 'pedestrian',
          value: 6.598968680078229,
        },
        {
          key: 'unknown',
          label: 'unknown',
          value: 4.108007942451715,
        },
        {
          key: 'steps',
          label: 'steps',
          value: 2.051443412037471,
        },
        {
          key: 'path',
          label: 'path',
          value: 0.31484656766063335,
        },
      ],
      context: [
        {
          key: 'pedestrian_km',
          label: 'Pedestrian-only network',
          value: 59.53004507038587,
          unit: 'km',
        },
        {
          key: 'network_km',
          label: 'All mapped network',
          value: 288.93703088227943,
          unit: 'km',
        },
      ],
    },
    {
      key: 'green_space_distance_p50',
      label: 'Median distance to a public green space of at least 0.5 ha',
      value: 362.4899425351278,
      unit: 'm',
      band: 'Beyond',
      definition:
        'Median straight-line distance from a building centroid inside the area to the nearest mapped public green space of at least 0.5 ha — parks, village greens, municipal gardens and recreation grounds — wherever that green space lies; the size floor and the 300 m band follow WHO Europe (2017).',
      not_claim:
        'Straight-line, not walking distance: a park across a railway reads as near. Only polygons Overture carries count, so interior courtyard gardens and pocket greens under 0.5 ha are ignored by design; pitches, stadiums, marinas and nurseries are excluded as not public green space. Linear street greening — tree-lined avenues and green axes such as Consell de Cent — is invisible to this KPI by design: it measures distance to green *areas* of at least 0.5 ha. Building centroids are not people.',
      denominator: 'building_count',
      lower_is_better: true,
      source: {
        kind: 'citation',
        label: 'WHO Europe, Urban green spaces: a brief for action (2017), p. 11',
        url: 'https://www.who.int/europe/publications/i/item/9789289052498',
        note: '"urban residents should be able to access public green spaces of at least 0.5–1 hectare within 300 metres\' linear distance (around 5 minutes\' walk) of their homes." The 600 m boundary is chosen: double the WHO distance.',
      },
      bands: [
        {
          label: 'Within WHO rule of thumb',
          max: 300.0,
        },
        {
          label: 'Beyond',
          max: 600.0,
        },
        {
          label: 'Far',
          max: null,
        },
      ],
      sample_size: 8397,
      breakdown: [
        {
          key: 'within_300',
          label: '≤ 300 m',
          value: 3418.0,
        },
        {
          key: 'within_600',
          label: '300–600 m',
          value: 3391.0,
        },
        {
          key: 'beyond_600',
          label: '> 600 m',
          value: 1588.0,
        },
      ],
      context: [
        {
          key: 'share_within_300',
          label: 'Buildings within 300 m',
          value: 40.70501369536739,
          unit: '%',
        },
        {
          key: 'targets',
          label: 'Green spaces ≥ 0.5 ha searched',
          value: 159.0,
          unit: '',
        },
      ],
    },
    {
      key: 'street_tree_density',
      label: 'Street trees per km of carriageway',
      value: 55.383444721952756,
      unit: '/km',
      band: 'Middle third',
      definition:
        'Mapped individual trees inside the area per kilometre of carriageway inside the area.',
      not_claim:
        "A shade and greenness proxy, not a safety measure. Canopy size, species and health are unknown; a sapling counts the same as a plane tree. Tree mapping is OSM-derived and can be uneven outside this district. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 20.0,
        },
        {
          label: 'Middle third',
          max: 69.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 1754,
      breakdown_note: 'No breakdown: Overture tree points carry no species, size or canopy.',
      context: [
        {
          key: 'trees',
          label: 'Trees in area',
          value: 8880.0,
          unit: '',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 160.3367223649808,
          unit: 'km',
        },
      ],
    },
  ],
  insights: [
    "51% of the 142.7 km of carriageway with a mapped limit is 30 km/h or less — the middle third of Eixample's 250 m cells.",
    'The median building is 362 m from the nearest public green space of at least 0.5 ha; only 41% of the 8,397 buildings are within the WHO 300 m rule of thumb.',
  ],
  legend: {
    type: 'categorical',
    items: [
      {
        kpi_key: 'low_speed_street_share',
        key: 'le20',
        label: '≤ 20 km/h',
        color: '#15803d',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'le30',
        label: '21–30 km/h',
        color: '#0f766e',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'le50',
        label: '31–50 km/h',
        color: '#b45309',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'gt50',
        label: '> 50 km/h',
        color: '#78350f',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'none',
        label: 'No mapped limit',
        color: '#94a3b8',
      },
      {
        kpi_key: 'crossing_density',
        key: 'crossing',
        label: 'crossing',
        color: '#1d4ed8',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'cycleway',
        label: 'cycleway',
        color: '#0f766e',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'residential',
        label: 'residential',
        color: '#b45309',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'footway',
        label: 'footway',
        color: '#15803d',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'secondary',
        label: 'secondary',
        color: '#4338ca',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'tertiary',
        label: 'tertiary',
        color: '#78350f',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'living_street',
        label: 'living_street',
        color: '#a16207',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'primary',
        label: 'primary',
        color: '#7e22ce',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'service',
        label: 'service',
        color: '#64748b',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'pedestrian',
        label: 'pedestrian',
        color: '#166534',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'unknown',
        label: 'unknown',
        color: '#94a3b8',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'steps',
        label: 'steps',
        color: '#4d7c0f',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'path',
        label: 'path',
        color: '#65a30d',
      },
      {
        kpi_key: 'green_space_distance_p50',
        key: 'within_300',
        label: '≤ 300 m',
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
        key: 'beyond_600',
        label: '> 600 m',
        color: '#7e22ce',
      },
      {
        kpi_key: 'street_tree_density',
        key: 'tree',
        label: 'tree',
        color: '#16a34a',
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
              id: '9ea11987-45a3-4f6b-ba9c-ec55d962398a',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.14499, 41.39275],
                  [2.14497, 41.39284],
                  [2.14496, 41.39285],
                ],
              },
              properties: {
                category: 'le50',
                name: 'Plaça de Francesc Macià',
                length_m: 19.6,
              },
            },
            {
              type: 'Feature',
              id: 'ebf28715-24e3-4ea9-8916-86a4b6c517ee',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.14533, 41.39295],
                  [2.1452, 41.39293],
                  [2.14516, 41.39292],
                ],
              },
              properties: {
                category: 'le50',
                name: 'Avinguda Diagonal',
                length_m: 35.0,
              },
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
              id: 'd3a4b1e1-84fa-3ef2-9280-c78961cd6e75',
              geometry: {
                type: 'Point',
                coordinates: [2.15525, 41.38157],
              },
              properties: {
                category: 'crossing',
              },
            },
            {
              type: 'Feature',
              id: '4d7c13ee-567c-3ab8-ab54-e3e086527d86',
              geometry: {
                type: 'Point',
                coordinates: [2.15281, 41.38137],
              },
              properties: {
                category: 'crossing',
              },
            },
          ],
        },
      },
      {
        id: 'streets_class',
        kpi_key: 'pedestrian_network_share',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: '9ea11987-45a3-4f6b-ba9c-ec55d962398a',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.14499, 41.39275],
                  [2.14497, 41.39284],
                  [2.14496, 41.39285],
                ],
              },
              properties: {
                category: 'secondary',
                name: 'Plaça de Francesc Macià',
                length_m: 19.6,
              },
            },
            {
              type: 'Feature',
              id: 'ebf28715-24e3-4ea9-8916-86a4b6c517ee',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.14533, 41.39295],
                  [2.1452, 41.39293],
                  [2.14516, 41.39292],
                ],
              },
              properties: {
                category: 'secondary',
                name: 'Avinguda Diagonal',
                length_m: 35.0,
              },
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
              id: '86bdd971-5b4e-421c-b645-d71127f949b7',
              geometry: {
                type: 'Point',
                coordinates: [2.14293, 41.38116],
              },
              properties: {
                category: 'within_300',
                distance_m: 190.0,
              },
            },
            {
              type: 'Feature',
              id: '93312c49-c0a2-4376-82a5-c5be3cc55d0c',
              geometry: {
                type: 'Point',
                coordinates: [2.14281, 41.38152],
              },
              properties: {
                category: 'within_300',
                distance_m: 153.1,
              },
            },
          ],
        },
      },
      {
        id: 'green_spaces',
        kpi_key: 'green_space_distance_p50',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: '41602b4f-48e6-3396-963d-5292617adbd4',
              geometry: {
                type: 'Polygon',
                coordinates: [
                  [
                    [2.17145, 41.41349],
                    [2.17144, 41.41359],
                    [2.17177, 41.41382],
                    [2.17197, 41.41367],
                    [2.172, 41.41366],
                    [2.17145, 41.41349],
                  ],
                ],
              },
              properties: {
                category: 'green_space',
                area_ha: 2.02,
              },
            },
            {
              type: 'Feature',
              id: 'e3270670-276b-3944-913d-133ae4b9458f',
              geometry: {
                type: 'Polygon',
                coordinates: [
                  [
                    [2.16885, 41.41024],
                    [2.16901, 41.41011],
                    [2.16887, 41.41],
                    [2.16918, 41.40977],
                    [2.16949, 41.40954],
                    [2.16885, 41.41024],
                  ],
                ],
              },
              properties: {
                category: 'green_space',
                name: 'Jardins del Baix Guinardó',
                area_ha: 1.91,
              },
            },
          ],
        },
      },
      {
        id: 'trees',
        kpi_key: 'street_tree_density',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: 'fde43f01-d93e-3f6d-b008-e12c1ebc6c01',
              geometry: {
                type: 'Point',
                coordinates: [2.14244, 41.38418],
              },
              properties: {
                category: 'tree',
              },
            },
            {
              type: 'Feature',
              id: '8c1b56b8-cfcb-3534-b02f-ef837fe25aab',
              geometry: {
                type: 'Point',
                coordinates: [2.14244, 41.38426],
              },
              properties: {
                category: 'tree',
              },
            },
          ],
        },
      },
    ],
  },
  meta: {
    computed_ms: 2100.0,
    cached: false,
    overture_release: '2026-08-19.0',
    warehouse_build: 'efebeffb8727',
    timings_ms: {
      low_speed_street_share: 90.9,
    },
  },
};

/** Reference area A — the Sant Antoni superblock (docs/reference-areas/). */
export const areaAResponse: KpiResponse = {
  area: {
    name: 'Drawn area',
    km2: 0.31767592503011,
    source: 'drawn',
    district_overlap_share: 0.9996582564789684,
  },
  kpis: [
    {
      key: 'low_speed_street_share',
      label: 'Carriageway limited to 30 km/h or less',
      value: 63.57575781241632,
      unit: '%',
      band: 'Upper third',
      definition:
        'Share of carriageway length inside the area whose posted speed limit is 30 km/h or lower, over the carriageway length that has a mapped limit at all.',
      not_claim:
        "A posted limit, not an observed speed. Carriageway without a mapped limit is excluded from both numerator and denominator, not assumed fast; the share excluded is shown alongside. Says nothing about enforcement, crashes or lane count. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label:
          "30 km/h: Real Decreto 970/2020 (BOE-A-2020-13969), art. 50 RGC; bands derived from Eixample's 250 m cells (P33 / P67)",
        url: 'https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969',
        note: "The 30 km/h threshold is the statutory urban limit for roads with one lane per direction since 11 May 2021 (art. 50.1 RGC: 20 km/h single-platform streets, 30 km/h one lane per direction, 50 km/h two or more). Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 42.0,
        },
        {
          label: 'Middle third',
          max: 60.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 54,
      breakdown: [
        {
          key: 'le20',
          label: '≤ 20 km/h',
          value: 1.695379845187669,
        },
        {
          key: 'le30',
          label: '21–30 km/h',
          value: 1.785833013078748,
        },
        {
          key: 'le50',
          label: '31–50 km/h',
          value: 1.9944794150965246,
        },
        {
          key: 'gt50',
          label: '> 50 km/h',
          value: 0.0,
        },
        {
          key: 'none',
          label: 'No mapped limit',
          value: 0.7462848179597282,
        },
      ],
      context: [
        {
          key: 'limit_coverage',
          label: 'Carriageway with a mapped limit',
          value: 88.0056643249215,
          unit: '%',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 6.2219770913226675,
          unit: 'km',
        },
        {
          key: 'mapped_km',
          label: 'Carriageway with a mapped limit',
          value: 5.475692273362941,
          unit: 'km',
        },
      ],
    },
    {
      key: 'crossing_density',
      label: 'Pedestrian crossings per km of carriageway',
      value: 20.89368027106712,
      unit: '/km',
      band: 'Middle third',
      definition:
        'Mapped pedestrian crossing points inside the area per kilometre of carriageway inside the area.',
      not_claim:
        "A crossing point carries no quality: signalised, raised, marked or lit are not known. High density does not mean safe crossing, and a pedestrianised area with no carriageway has nothing to cross and reads as no data, not as zero. In shared-space or living streets, fewer marked crossings can mean the whole street has become crossable; a low reading there is not a deficit. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "No standard I could verify prescribes crossings per kilometre. Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 19.0,
        },
        {
          label: 'Middle third',
          max: 26.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 66,
      breakdown_note:
        'No breakdown: Overture carries no attributes on a crossing point to split by.',
      context: [
        {
          key: 'crossings',
          label: 'Crossings in area',
          value: 130.0,
          unit: '',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 6.2219770913226675,
          unit: 'km',
        },
      ],
    },
    {
      key: 'pedestrian_network_share',
      label: 'Street network that is pedestrian-only (sidewalks excluded)',
      value: 26.02652475678809,
      unit: '%',
      band: 'Upper third',
      definition:
        'Share of the mapped street network length inside the area that is pedestrian-only geometry — pedestrian streets, footways, steps and paths — with sidewalk and crosswalk geometry excluded from both sides.',
      not_claim:
        "Street space given over to walking, not sidewalk provision: sidewalks and crosswalks are deliberately excluded because their mapping is incomplete. Says nothing about sidewalk width, quality or continuity. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'network_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "Sidewalks are excluded because Overture maps only about half of Barcelona's sidewalks as separate lines (mapped sidewalk km per carriageway km ranges from 0.7 to 1.5 across cells, median 1.1): with them in, the KPI measured mapping coverage, not the street. Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 14.0,
        },
        {
          label: 'Middle third',
          max: 24.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 139,
      breakdown: [
        {
          key: 'footway',
          label: 'footway',
          value: 2.4759539631035357,
        },
        {
          key: 'cycleway',
          label: 'cycleway',
          value: 2.0474499199061023,
        },
        {
          key: 'living_street',
          label: 'living_street',
          value: 1.6953798451876692,
        },
        {
          key: 'residential',
          label: 'residential',
          value: 1.4194076342505955,
        },
        {
          key: 'tertiary',
          label: 'tertiary',
          value: 1.0048704290554098,
        },
        {
          key: 'service',
          label: 'service',
          value: 0.8327026232173306,
        },
        {
          key: 'secondary',
          label: 'secondary',
          value: 0.7940760825027753,
        },
        {
          key: 'primary',
          label: 'primary',
          value: 0.4001000937472026,
        },
        {
          key: 'pedestrian',
          label: 'pedestrian',
          value: 0.34832011028759646,
        },
        {
          key: 'steps',
          label: 'steps',
          value: 0.08520727954757346,
        },
        {
          key: 'unknown',
          label: 'unknown',
          value: 0.07544038336168708,
        },
      ],
      context: [
        {
          key: 'pedestrian_km',
          label: 'Pedestrian-only network',
          value: 2.9094813529387045,
          unit: 'km',
        },
        {
          key: 'network_km',
          label: 'All mapped network',
          value: 11.178908364167482,
          unit: 'km',
        },
      ],
    },
    {
      key: 'green_space_distance_p50',
      label: 'Median distance to a public green space of at least 0.5 ha',
      value: 594.6679121056678,
      unit: 'm',
      band: 'Beyond',
      definition:
        'Median straight-line distance from a building centroid inside the area to the nearest mapped public green space of at least 0.5 ha — parks, village greens, municipal gardens and recreation grounds — wherever that green space lies; the size floor and the 300 m band follow WHO Europe (2017).',
      not_claim:
        'Straight-line, not walking distance: a park across a railway reads as near. Only polygons Overture carries count, so interior courtyard gardens and pocket greens under 0.5 ha are ignored by design; pitches, stadiums, marinas and nurseries are excluded as not public green space. Linear street greening — tree-lined avenues and green axes such as Consell de Cent — is invisible to this KPI by design: it measures distance to green *areas* of at least 0.5 ha. Building centroids are not people.',
      denominator: 'building_count',
      lower_is_better: true,
      source: {
        kind: 'citation',
        label: 'WHO Europe, Urban green spaces: a brief for action (2017), p. 11',
        url: 'https://www.who.int/europe/publications/i/item/9789289052498',
        note: '"urban residents should be able to access public green spaces of at least 0.5–1 hectare within 300 metres\' linear distance (around 5 minutes\' walk) of their homes." The 600 m boundary is chosen: double the WHO distance.',
      },
      bands: [
        {
          label: 'Within WHO rule of thumb',
          max: 300.0,
        },
        {
          label: 'Beyond',
          max: 600.0,
        },
        {
          label: 'Far',
          max: null,
        },
      ],
      sample_size: 477,
      breakdown: [
        {
          key: 'within_300',
          label: '≤ 300 m',
          value: 0.0,
        },
        {
          key: 'within_600',
          label: '300–600 m',
          value: 250.0,
        },
        {
          key: 'beyond_600',
          label: '> 600 m',
          value: 227.0,
        },
      ],
      context: [
        {
          key: 'share_within_300',
          label: 'Buildings within 300 m',
          value: 0.0,
          unit: '%',
        },
        {
          key: 'targets',
          label: 'Green spaces ≥ 0.5 ha searched',
          value: 159.0,
          unit: '',
        },
      ],
    },
    {
      key: 'street_tree_density',
      label: 'Street trees per km of carriageway',
      value: 52.71636253007704,
      unit: '/km',
      band: 'Middle third',
      definition:
        'Mapped individual trees inside the area per kilometre of carriageway inside the area.',
      not_claim:
        "A shade and greenness proxy, not a safety measure. Canopy size, species and health are unknown; a sapling counts the same as a plane tree. Tree mapping is OSM-derived and can be uneven outside this district. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 20.0,
        },
        {
          label: 'Middle third',
          max: 69.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 66,
      breakdown_note: 'No breakdown: Overture tree points carry no species, size or canopy.',
      context: [
        {
          key: 'trees',
          label: 'Trees in area',
          value: 328.0,
          unit: '',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 6.2219770913226675,
          unit: 'km',
        },
      ],
    },
  ],
  insights: [
    "64% of the 5.5 km of carriageway with a mapped limit is 30 km/h or less — a higher share than two thirds of Eixample's 250 m cells.",
    'The median building is 595 m from the nearest public green space of at least 0.5 ha; none of the 477 buildings are within the WHO 300 m rule of thumb.',
    "26% of the street network (2.9 km) is pedestrian-only space — more than in two thirds of Eixample's 250 m cells.",
  ],
  legend: {
    type: 'categorical',
    items: [
      {
        kpi_key: 'low_speed_street_share',
        key: 'le20',
        label: '≤ 20 km/h',
        color: '#15803d',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'le30',
        label: '21–30 km/h',
        color: '#0f766e',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'le50',
        label: '31–50 km/h',
        color: '#b45309',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'gt50',
        label: '> 50 km/h',
        color: '#78350f',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'none',
        label: 'No mapped limit',
        color: '#94a3b8',
      },
      {
        kpi_key: 'crossing_density',
        key: 'crossing',
        label: 'crossing',
        color: '#1d4ed8',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'footway',
        label: 'footway',
        color: '#15803d',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'cycleway',
        label: 'cycleway',
        color: '#0f766e',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'living_street',
        label: 'living_street',
        color: '#a16207',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'residential',
        label: 'residential',
        color: '#b45309',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'tertiary',
        label: 'tertiary',
        color: '#78350f',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'service',
        label: 'service',
        color: '#64748b',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'secondary',
        label: 'secondary',
        color: '#4338ca',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'primary',
        label: 'primary',
        color: '#7e22ce',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'pedestrian',
        label: 'pedestrian',
        color: '#166534',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'steps',
        label: 'steps',
        color: '#4d7c0f',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'unknown',
        label: 'unknown',
        color: '#94a3b8',
      },
      {
        kpi_key: 'green_space_distance_p50',
        key: 'within_300',
        label: '≤ 300 m',
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
        key: 'beyond_600',
        label: '> 600 m',
        color: '#7e22ce',
      },
      {
        kpi_key: 'street_tree_density',
        key: 'tree',
        label: 'tree',
        color: '#16a34a',
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
              id: 'db343996-4cb7-4cb4-86cb-3f389fe3746d',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.15348, 41.38188],
                  [2.15376, 41.38208],
                  [2.15387, 41.38208],
                ],
              },
              properties: {
                category: 'le20',
                name: 'Carrer del Consell de Cent',
                length_m: 61.6,
              },
            },
            {
              type: 'Feature',
              id: '483e1922-896d-4944-9ed7-cdd5372315b8',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.15373, 41.3824],
                  [2.15381, 41.38233],
                ],
              },
              properties: {
                category: 'le30',
                name: 'Carrer de Viladomat',
                length_m: 9.8,
              },
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
              id: 'd3a4b1e1-84fa-3ef2-9280-c78961cd6e75',
              geometry: {
                type: 'Point',
                coordinates: [2.15525, 41.38157],
              },
              properties: {
                category: 'crossing',
              },
            },
            {
              type: 'Feature',
              id: 'fac88b3a-234b-37fb-a28f-8c585027bea3',
              geometry: {
                type: 'Point',
                coordinates: [2.15394, 41.38224],
              },
              properties: {
                category: 'crossing',
              },
            },
          ],
        },
      },
      {
        id: 'streets_class',
        kpi_key: 'pedestrian_network_share',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: 'db343996-4cb7-4cb4-86cb-3f389fe3746d',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.15348, 41.38188],
                  [2.15376, 41.38208],
                  [2.15387, 41.38208],
                ],
              },
              properties: {
                category: 'living_street',
                name: 'Carrer del Consell de Cent',
                length_m: 61.6,
              },
            },
            {
              type: 'Feature',
              id: '483e1922-896d-4944-9ed7-cdd5372315b8',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [2.15373, 41.3824],
                  [2.15381, 41.38233],
                ],
              },
              properties: {
                category: 'residential',
                name: 'Carrer de Viladomat',
                length_m: 9.8,
              },
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
              id: '55f93c0e-e9ff-4585-b338-edcbc5c46bb2',
              geometry: {
                type: 'Point',
                coordinates: [2.1536, 41.38226],
              },
              properties: {
                category: 'within_600',
                distance_m: 526.8,
              },
            },
            {
              type: 'Feature',
              id: '8b9f1bc1-fec8-4994-8c15-1b7ba4d40927',
              geometry: {
                type: 'Point',
                coordinates: [2.15346, 41.38214],
              },
              properties: {
                category: 'within_600',
                distance_m: 509.1,
              },
            },
          ],
        },
      },
      {
        id: 'green_spaces',
        kpi_key: 'green_space_distance_p50',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: '03b360ec-57d6-3430-a194-165b003f10be',
              geometry: {
                type: 'Polygon',
                coordinates: [
                  [
                    [2.16628, 41.37653],
                    [2.16629, 41.37653],
                    [2.1663, 41.37654],
                    [2.1665, 41.37669],
                    [2.16649, 41.3767],
                    [2.16628, 41.37653],
                  ],
                ],
              },
              properties: {
                category: 'green_space',
                name: 'Plaça de Josep M. Folch i Torres',
                area_ha: 0.54,
              },
            },
            {
              type: 'Feature',
              id: 'b64ca2c8-0107-3912-8ece-83bf0e7dfa1c',
              geometry: {
                type: 'Polygon',
                coordinates: [
                  [
                    [2.16309, 41.38585],
                    [2.16286, 41.38585],
                    [2.16279, 41.3859],
                    [2.16284, 41.38594],
                    [2.16288, 41.3859],
                    [2.16309, 41.38585],
                  ],
                ],
              },
              properties: {
                category: 'green_space',
                name: 'Jardí Ferran Soldevila',
                area_ha: 0.98,
              },
            },
          ],
        },
      },
      {
        id: 'trees',
        kpi_key: 'street_tree_density',
        data: {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              id: '26c24bf0-60a8-3530-a58b-2165c17777c2',
              geometry: {
                type: 'Point',
                coordinates: [2.15645, 41.38042],
              },
              properties: {
                category: 'tree',
              },
            },
            {
              type: 'Feature',
              id: '18e55281-bcd7-3694-8cc8-5d150fba28e8',
              geometry: {
                type: 'Point',
                coordinates: [2.1565, 41.38038],
              },
              properties: {
                category: 'tree',
              },
            },
          ],
        },
      },
    ],
  },
  meta: {
    computed_ms: 2100.0,
    cached: false,
    overture_release: '2026-08-19.0',
    warehouse_build: 'efebeffb8727',
    timings_ms: {
      low_speed_street_share: 90.9,
    },
  },
};

/** A polygon with no features: the empty state. Values nulled from the district. */
export const emptyResponse: KpiResponse = {
  area: {
    name: 'Drawn area',
    km2: 1.46,
    source: 'drawn',
    district_overlap_share: 0.0,
  },
  kpis: [
    {
      key: 'low_speed_street_share',
      label: 'Carriageway limited to 30 km/h or less',
      value: null,
      unit: '%',
      band: null,
      definition:
        'Share of carriageway length inside the area whose posted speed limit is 30 km/h or lower, over the carriageway length that has a mapped limit at all.',
      not_claim:
        "A posted limit, not an observed speed. Carriageway without a mapped limit is excluded from both numerator and denominator, not assumed fast; the share excluded is shown alongside. Says nothing about enforcement, crashes or lane count. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label:
          "30 km/h: Real Decreto 970/2020 (BOE-A-2020-13969), art. 50 RGC; bands derived from Eixample's 250 m cells (P33 / P67)",
        url: 'https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969',
        note: "The 30 km/h threshold is the statutory urban limit for roads with one lane per direction since 11 May 2021 (art. 50.1 RGC: 20 km/h single-platform streets, 30 km/h one lane per direction, 50 km/h two or more). Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 42.0,
        },
        {
          label: 'Middle third',
          max: 60.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 0,
      context: [
        {
          key: 'limit_coverage',
          label: 'Carriageway with a mapped limit',
          value: 89.01131980366338,
          unit: '%',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 160.3367223649808,
          unit: 'km',
        },
        {
          key: 'mapped_km',
          label: 'Carriageway with a mapped limit',
          value: 142.71783270700493,
          unit: 'km',
        },
      ],
    },
    {
      key: 'crossing_density',
      label: 'Pedestrian crossings per km of carriageway',
      value: null,
      unit: '/km',
      band: null,
      definition:
        'Mapped pedestrian crossing points inside the area per kilometre of carriageway inside the area.',
      not_claim:
        "A crossing point carries no quality: signalised, raised, marked or lit are not known. High density does not mean safe crossing, and a pedestrianised area with no carriageway has nothing to cross and reads as no data, not as zero. In shared-space or living streets, fewer marked crossings can mean the whole street has become crossable; a low reading there is not a deficit. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "No standard I could verify prescribes crossings per kilometre. Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 19.0,
        },
        {
          label: 'Middle third',
          max: 26.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 0,
      breakdown_note:
        'No breakdown: Overture carries no attributes on a crossing point to split by.',
      context: [
        {
          key: 'crossings',
          label: 'Crossings in area',
          value: 3624.0,
          unit: '',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 160.3367223649808,
          unit: 'km',
        },
      ],
    },
    {
      key: 'pedestrian_network_share',
      label: 'Street network that is pedestrian-only (sidewalks excluded)',
      value: null,
      unit: '%',
      band: null,
      definition:
        'Share of the mapped street network length inside the area that is pedestrian-only geometry — pedestrian streets, footways, steps and paths — with sidewalk and crosswalk geometry excluded from both sides.',
      not_claim:
        "Street space given over to walking, not sidewalk provision: sidewalks and crosswalks are deliberately excluded because their mapping is incomplete. Says nothing about sidewalk width, quality or continuity. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'network_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "Sidewalks are excluded because Overture maps only about half of Barcelona's sidewalks as separate lines (mapped sidewalk km per carriageway km ranges from 0.7 to 1.5 across cells, median 1.1): with them in, the KPI measured mapping coverage, not the street. Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 14.0,
        },
        {
          label: 'Middle third',
          max: 24.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 0,
      context: [
        {
          key: 'pedestrian_km',
          label: 'Pedestrian-only network',
          value: 59.53004507038587,
          unit: 'km',
        },
        {
          key: 'network_km',
          label: 'All mapped network',
          value: 288.93703088227943,
          unit: 'km',
        },
      ],
    },
    {
      key: 'green_space_distance_p50',
      label: 'Median distance to a public green space of at least 0.5 ha',
      value: null,
      unit: 'm',
      band: null,
      definition:
        'Median straight-line distance from a building centroid inside the area to the nearest mapped public green space of at least 0.5 ha — parks, village greens, municipal gardens and recreation grounds — wherever that green space lies; the size floor and the 300 m band follow WHO Europe (2017).',
      not_claim:
        'Straight-line, not walking distance: a park across a railway reads as near. Only polygons Overture carries count, so interior courtyard gardens and pocket greens under 0.5 ha are ignored by design; pitches, stadiums, marinas and nurseries are excluded as not public green space. Linear street greening — tree-lined avenues and green axes such as Consell de Cent — is invisible to this KPI by design: it measures distance to green *areas* of at least 0.5 ha. Building centroids are not people.',
      denominator: 'building_count',
      lower_is_better: true,
      source: {
        kind: 'citation',
        label: 'WHO Europe, Urban green spaces: a brief for action (2017), p. 11',
        url: 'https://www.who.int/europe/publications/i/item/9789289052498',
        note: '"urban residents should be able to access public green spaces of at least 0.5–1 hectare within 300 metres\' linear distance (around 5 minutes\' walk) of their homes." The 600 m boundary is chosen: double the WHO distance.',
      },
      bands: [
        {
          label: 'Within WHO rule of thumb',
          max: 300.0,
        },
        {
          label: 'Beyond',
          max: 600.0,
        },
        {
          label: 'Far',
          max: null,
        },
      ],
      sample_size: 0,
      context: [
        {
          key: 'share_within_300',
          label: 'Buildings within 300 m',
          value: 40.70501369536739,
          unit: '%',
        },
        {
          key: 'targets',
          label: 'Green spaces ≥ 0.5 ha searched',
          value: 159.0,
          unit: '',
        },
      ],
    },
    {
      key: 'street_tree_density',
      label: 'Street trees per km of carriageway',
      value: null,
      unit: '/km',
      band: null,
      definition:
        'Mapped individual trees inside the area per kilometre of carriageway inside the area.',
      not_claim:
        "A shade and greenness proxy, not a safety measure. Canopy size, species and health are unknown; a sapling counts the same as a plane tree. Tree mapping is OSM-derived and can be uneven outside this district. Bands are relative to Eixample's own distribution, not an absolute standard.",
      denominator: 'carriageway_length_m',
      lower_is_better: false,
      source: {
        kind: 'derived',
        label: "Derived from Eixample's 250 m cells (P33 / P67)",
        url: null,
        note: "Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two significant figures). They are relative to Eixample's own distribution, not an absolute standard. Method: backend/pipeline/derive_bands.py.",
      },
      bands: [
        {
          label: 'Lower third',
          max: 20.0,
        },
        {
          label: 'Middle third',
          max: 69.0,
        },
        {
          label: 'Upper third',
          max: null,
        },
      ],
      sample_size: 0,
      breakdown_note: 'No breakdown: Overture tree points carry no species, size or canopy.',
      context: [
        {
          key: 'trees',
          label: 'Trees in area',
          value: 8880.0,
          unit: '',
        },
        {
          key: 'carriageway_km',
          label: 'Carriageway in area',
          value: 160.3367223649808,
          unit: 'km',
        },
      ],
    },
  ],
  insights: [
    'The 1.46 km² area contains none of the features the KPIs measure; try a larger or different polygon.',
  ],
  legend: {
    type: 'categorical',
    items: [
      {
        kpi_key: 'low_speed_street_share',
        key: 'le20',
        label: '≤ 20 km/h',
        color: '#15803d',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'le30',
        label: '21–30 km/h',
        color: '#0f766e',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'le50',
        label: '31–50 km/h',
        color: '#b45309',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'gt50',
        label: '> 50 km/h',
        color: '#78350f',
      },
      {
        kpi_key: 'low_speed_street_share',
        key: 'none',
        label: 'No mapped limit',
        color: '#94a3b8',
      },
      {
        kpi_key: 'crossing_density',
        key: 'crossing',
        label: 'crossing',
        color: '#1d4ed8',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'cycleway',
        label: 'cycleway',
        color: '#0f766e',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'residential',
        label: 'residential',
        color: '#b45309',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'footway',
        label: 'footway',
        color: '#15803d',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'secondary',
        label: 'secondary',
        color: '#4338ca',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'tertiary',
        label: 'tertiary',
        color: '#78350f',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'living_street',
        label: 'living_street',
        color: '#a16207',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'primary',
        label: 'primary',
        color: '#7e22ce',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'service',
        label: 'service',
        color: '#64748b',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'pedestrian',
        label: 'pedestrian',
        color: '#166534',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'unknown',
        label: 'unknown',
        color: '#94a3b8',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'steps',
        label: 'steps',
        color: '#4d7c0f',
      },
      {
        kpi_key: 'pedestrian_network_share',
        key: 'path',
        label: 'path',
        color: '#65a30d',
      },
      {
        kpi_key: 'green_space_distance_p50',
        key: 'within_300',
        label: '≤ 300 m',
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
        key: 'beyond_600',
        label: '> 600 m',
        color: '#7e22ce',
      },
      {
        kpi_key: 'street_tree_density',
        key: 'tree',
        label: 'tree',
        color: '#16a34a',
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
          features: [],
        },
      },
      {
        id: 'crossings',
        kpi_key: 'crossing_density',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      },
      {
        id: 'streets_class',
        kpi_key: 'pedestrian_network_share',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      },
      {
        id: 'buildings_green',
        kpi_key: 'green_space_distance_p50',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      },
      {
        id: 'green_spaces',
        kpi_key: 'green_space_distance_p50',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      },
      {
        id: 'trees',
        kpi_key: 'street_tree_density',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      },
    ],
  },
  meta: {
    computed_ms: 2100.0,
    cached: false,
    overture_release: '2026-08-19.0',
    warehouse_build: 'efebeffb8727',
    timings_ms: {
      low_speed_street_share: 90.9,
    },
  },
};
