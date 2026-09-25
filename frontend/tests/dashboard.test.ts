/**
 * The dashboard's pure seams: the contribution calculator (one rule per KPI) and the band
 * ramp (single hue, ordered by lower_is_better, never a traffic light).
 *
 * The contribution cases run against the captured district response, whose layers carry two
 * real features each — real GERS ids, real names, real clipped lengths. The shares are
 * therefore "of the two features the fixture holds", which is exactly what the function
 * computes over the layer it is given.
 */

import { describe, expect, it } from 'vitest';

import { bandStyle, rampFor } from '@/features/dashboard/bands';
import { describeContribution } from '@/features/dashboard/contribution';

import { districtResponse as r } from './fixtures/kpiResponse';

const STREET_A = '9ea11987-45a3-4f6b-ba9c-ec55d962398a'; // Plaça de Francesc Macià, 19.6 m
const STREET_B = 'ebf28715-24e3-4ea9-8916-86a4b6c517ee'; // Avinguda Diagonal, 35.0 m
const CROSSING = 'd3a4b1e1-84fa-3ef2-9280-c78961cd6e75';
const BUILDING = '86bdd971-5b4e-421c-b645-d71127f949b7'; // 190.0 m to its nearest green
const GREEN = '41602b4f-48e6-3396-963d-5292617adbd4'; // 2.02 ha, unnamed

describe('contribution (map -> dashboard), one rule per KPI', () => {
  it('street: clipped length and share of the carriageway in the layer, by name', () => {
    expect(describeContribution(r, 'low_speed_street_share', STREET_A)).toEqual({
      title: 'Plaça de Francesc Macià',
      layerId: 'streets_speed',
      detail:
        'Plaça de Francesc Macià: 20 m of carriageway posted 31–50 km/h, 36 % of the ' +
        'carriageway in this area.',
    });
  });

  it('pedestrian network: the same feature, described against its own KPI', () => {
    expect(describeContribution(r, 'pedestrian_network_share', STREET_B)?.detail).toBe(
      'Avinguda Diagonal: 35 m of secondary, 64 % of the mapped network in this area.',
    );
  });

  it('crossing: 1 of N', () => {
    expect(describeContribution(r, 'crossing_density', CROSSING)?.detail).toBe(
      'crossing: 1 of 2 crossings in this area.',
    );
  });

  it('building: distance and the share of buildings that are nearer', () => {
    expect(describeContribution(r, 'green_space_distance_p50', BUILDING)?.detail).toBe(
      '≤ 300 m: 190 m to the nearest green space of at least 0.5 ha — further than 50 % of ' +
        'the buildings in this area.',
    );
  });

  it('green space: an unnamed park falls back to its category label', () => {
    const contribution = describeContribution(r, 'green_space_distance_p50', GREEN);
    expect(contribution?.title).toBe('green space');
    expect(contribution?.detail).toContain('2.02 ha');
  });

  it('returns null when the feature is not in the active KPI layers', () => {
    expect(describeContribution(r, 'crossing_density', STREET_A)).toBeNull();
    expect(describeContribution(r, 'nope', STREET_A)).toBeNull();
  });
});

describe('band ramp', () => {
  const bands = [
    { label: 'Lower third', max: 19 },
    { label: 'Middle third', max: 26 },
    { label: 'Upper third', max: null },
  ];

  it('spreads N bands from light to dark', () => {
    expect(rampFor(3)).toEqual(['#e0f2fe', '#0284c7', '#0c4a6e']);
    expect(rampFor(1)).toEqual(['#0c4a6e']);
  });

  it('higher-is-better: the last band is darkest; lower-is-better: the first is', () => {
    expect(bandStyle({ bands, band: 'Upper third', lower_is_better: false })).toMatchObject({
      rank: 2,
      total: 3,
      background: '#0c4a6e',
      color: '#ffffff',
    });
    expect(bandStyle({ bands, band: 'Lower third', lower_is_better: true })).toMatchObject({
      rank: 2,
      background: '#0c4a6e',
    });
    expect(bandStyle({ bands, band: 'Lower third', lower_is_better: false })).toMatchObject({
      rank: 0,
      background: '#e0f2fe',
      color: '#0c4a6e',
    });
    expect(bandStyle({ bands, band: null, lower_is_better: false })).toBeNull();
  });

  it('is blue-dominant at every step: no red, amber or green', () => {
    for (const hex of rampFor(6)) {
      const [red, green, blue] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
      expect(blue).toBeGreaterThanOrEqual(Math.max(red ?? 0, green ?? 0));
    }
  });

  it('the green KPI is the one that bands against an absolute distance', () => {
    const green = r.kpis.find((k) => k.key === 'green_space_distance_p50');
    expect(green?.source.kind).toBe('citation');
    expect(green?.lower_is_better).toBe(true);
    // Every other KPI bands against Eixample's own distribution.
    for (const kpi of r.kpis.filter((k) => k.key !== 'green_space_distance_p50')) {
      expect(kpi.source.kind).toBe('derived');
      expect(kpi.bands.map((b) => b.label)).toEqual(['Lower third', 'Middle third', 'Upper third']);
    }
  });
});
