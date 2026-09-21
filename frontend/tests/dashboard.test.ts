/**
 * The dashboard's pure seams: the contribution calculator (one rule per KPI) and the band
 * ramp (single hue, ordered by lower_is_better, never a traffic light).
 */

import { describe, expect, it } from 'vitest';

import { bandStyle, rampFor } from '@/features/dashboard/bands';
import { describeContribution } from '@/features/dashboard/contribution';

import { districtResponse as r } from './fixtures/kpiResponse';

describe('contribution (map -> dashboard), one rule per KPI', () => {
  it('street: clipped length and share of the carriageway in the area, by name', () => {
    expect(describeContribution(r, 'low_speed_street_share', 'seg-a')).toEqual({
      title: "Carrer d'Aragó",
      layerId: 'streets_speed',
      detail:
        "Carrer d'Aragó: 182 m of carriageway posted 30 km/h or less, 42 % of the carriageway in this area.",
    });
  });

  it('unnamed street falls back to the category label', () => {
    expect(describeContribution(r, 'low_speed_street_share', 'seg-b')?.title).toBe('31–50 km/h');
  });

  it('crossing: 1 of N', () => {
    expect(describeContribution(r, 'crossing_density', 'cross-a')?.detail).toBe(
      'crossing: 1 of 1 crossings in this area.',
    );
  });

  it('building: distance and the share of buildings that are nearer', () => {
    expect(describeContribution(r, 'green_space_distance_p50', 'bld-a')?.detail).toBe(
      '300–600 m: 412 m to the nearest green space of at least 0.5 ha — further than 50 % of the buildings in this area.',
    );
  });

  it('returns null when the feature is not in the active KPI layers', () => {
    expect(describeContribution(r, 'crossing_density', 'seg-a')).toBeNull();
    expect(describeContribution(r, 'nope', 'seg-a')).toBeNull();
  });
});

describe('band ramp', () => {
  const bands = [
    { label: 'Sparse', max: 10 },
    { label: 'Moderate', max: 20 },
    { label: 'Dense', max: null },
  ];

  it('spreads N bands from light to dark', () => {
    expect(rampFor(3)).toEqual(['#e0f2fe', '#0284c7', '#0c4a6e']);
    expect(rampFor(1)).toEqual(['#0c4a6e']);
  });

  it('higher-is-better: the last band is darkest; lower-is-better: the first is', () => {
    expect(bandStyle({ bands, band: 'Dense', lower_is_better: false })).toMatchObject({
      rank: 2,
      total: 3,
      background: '#0c4a6e',
      color: '#ffffff',
    });
    expect(bandStyle({ bands, band: 'Sparse', lower_is_better: true })).toMatchObject({
      rank: 2,
      background: '#0c4a6e',
    });
    expect(bandStyle({ bands, band: 'Sparse', lower_is_better: false })).toMatchObject({
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
});
