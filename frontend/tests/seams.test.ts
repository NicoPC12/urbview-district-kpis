/**
 * The pure seams the map delegates to, tested without WebGL.
 */

import { describe, expect, it } from 'vitest';

import { PROMOTE_ID, toFeature, toFeatureCollection, toGeometry } from '@/api/geojson';
import { finishDrawing } from '@/features/area/selection';
import { areaFromSearch, searchForArea } from '@/features/area/url';
import {
  colorExpression,
  emphasisExpression,
  highlightPaint,
  layerIds,
  layerSpecs,
  selectedFilter,
} from '@/features/map/layers';
import { districtArea, useAppStore } from '@/state/store';

import { districtResponse } from './fixtures/kpiResponse';

const RING = [
  [2.16, 41.39],
  [2.17, 41.39],
  [2.17, 41.397],
  [2.16, 41.39],
];

describe('finishDrawing', () => {
  it('turns a closed polygon ring into a drawn area', () => {
    const result = finishDrawing({ type: 'Polygon', coordinates: [RING] });
    expect(result).toEqual({
      ok: true,
      area: { kind: 'drawn', geometry: { type: 'Polygon', coordinates: [RING] } },
    });
  });

  it.each([
    [undefined, 'No geometry'],
    [{ type: 'Point', coordinates: [2.16, 41.39] }, 'Only a polygon'],
    [{ type: 'Polygon', coordinates: [RING, RING] }, 'one ring'],
    [
      {
        type: 'Polygon',
        coordinates: [
          [
            [2.16, 41.39],
            [2.17, 'x'],
            [2.16, 41.39],
          ],
        ],
      },
      'one ring',
    ],
    [
      {
        type: 'Polygon',
        coordinates: [
          [
            [2.16, 41.39],
            [2.17, 41.39],
            [2.16, 41.39],
          ],
        ],
      },
      'at least three',
    ],
    [{ type: 'Polygon', coordinates: [RING.slice(0, 3).concat([[2.0, 41.0]])] }, 'not closed'],
    [
      {
        type: 'Polygon',
        coordinates: [
          [
            [200, 41.39],
            [2.17, 41.39],
            [2.17, 41.4],
            [200, 41.39],
          ],
        ],
      },
      'one ring',
    ],
  ])('refuses %j', (geometry, reason) => {
    const result = finishDrawing(geometry);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toContain(reason);
  });
});

describe('geojson adapter', () => {
  it('promotes the GERS id into properties so MapLibre can address the feature', () => {
    const layer = districtResponse.layers.vectors[0];
    if (layer === undefined) throw new Error('fixture has no layers');
    const collection = toFeatureCollection(layer.data);
    const first = collection.features[0];
    expect(first?.id).toBe('seg-a');
    expect(first?.properties[PROMOTE_ID]).toBe('seg-a');
    expect(first?.properties.name).toBe("Carrer d'Aragó");
    expect(first?.geometry.type).toBe('LineString');
  });

  it('keeps optional properties absent rather than null', () => {
    const feature = toFeature({
      type: 'Feature',
      id: 'x',
      geometry: { type: 'Point', coordinates: [1, 2] },
      properties: { category: 'tree' },
    });
    expect('name' in feature.properties).toBe(false);
  });

  it('refuses coordinates that do not match the geometry type', () => {
    expect(() => toGeometry({ type: 'Polygon', coordinates: [1, 2] })).toThrow('Polygon');
  });
});

describe('highlight expressions (dashboard → map)', () => {
  const legend = districtResponse.legend.items.filter(
    (i) => i.kpi_key === 'low_speed_street_share',
  );

  it('colours by category from the legend with a fallback', () => {
    expect(colorExpression(legend)).toEqual([
      'match',
      ['get', 'category'],
      'le30',
      '#0f766e',
      'le50',
      '#b45309',
      'none',
      '#94a3b8',
      '#94a3b8',
    ]);
    expect(colorExpression([])).toBe('#94a3b8');
  });

  it('emphasises the selected category and dims the rest; nothing selected means no dimming', () => {
    expect(emphasisExpression(null, 1)).toBe(1);
    expect(emphasisExpression('le30', 1)).toEqual([
      'case',
      ['==', ['get', 'category'], 'le30'],
      1,
      0.2,
    ]);
  });

  it('outlines only the selected feature by promoted id', () => {
    expect(selectedFilter('seg-a')).toEqual(['==', ['get', 'id'], 'seg-a']);
    expect(selectedFilter(null)).toEqual(['==', ['get', 'id'], '']);
  });

  it('builds one layer per geometry type plus selection layers, all on the scoped source', () => {
    const specs = layerSpecs('area', 'streets_speed', legend, {
      selectedCategory: 'le30',
      selectedFeatureId: 'seg-a',
    });
    expect(specs.map((s) => s.id)).toEqual(layerIds('area', 'streets_speed'));
    expect(specs.every((s) => 'source' in s && s.source === 'area:streets_speed')).toBe(true);
    const line = specs.find((s) => s.id === 'area:streets_speed:line');
    expect(line?.paint).toMatchObject({
      'line-opacity': ['case', ['==', ['get', 'category'], 'le30'], 1, 0.2],
    });
  });

  it('context layers are dimmed and never carry a selection', () => {
    const specs = layerSpecs('context', 'streets_speed', legend, {
      selectedCategory: 'le30',
      selectedFeatureId: 'seg-a',
    });
    const line = specs.find((s) => s.id === 'context:streets_speed:line');
    expect(line?.paint).toMatchObject({ 'line-opacity': 0.35 });
    expect(
      highlightPaint('context', 'streets_speed', {
        selectedCategory: 'le30',
        selectedFeatureId: 'x',
      }),
    ).toEqual({
      paint: {},
      filters: {},
    });
  });

  it('updates paint and filters in place when the selection changes', () => {
    const { paint, filters } = highlightPaint('area', 'streets_speed', {
      selectedCategory: null,
      selectedFeatureId: 'seg-b',
    });
    expect(paint['area:streets_speed:line']).toEqual(['line-opacity', 1]);
    expect(filters['area:streets_speed:selected-line']).toEqual([
      'all',
      ['!=', ['geometry-type'], 'Point'],
      ['==', ['get', 'id'], 'seg-b'],
    ]);
  });
});

describe('store', () => {
  it('a new area clears any highlight and leaves draw mode; clearArea returns to the district', () => {
    const store = useAppStore.getState();
    store.setActiveKpi('low_speed_street_share');
    store.toggleCategory('le30');
    store.selectFeature('seg-a');
    store.setMode('draw');
    store.setArea({ kind: 'drawn', geometry: { type: 'Polygon', coordinates: [RING] } });
    expect(useAppStore.getState()).toMatchObject({
      selectedCategory: null,
      selectedFeatureId: null,
      mode: 'inspect',
      activeKpiKey: 'low_speed_street_share',
    });
    useAppStore.getState().clearArea();
    expect(useAppStore.getState().area).toEqual(districtArea());
  });

  it('toggling the same category twice clears it', () => {
    useAppStore.getState().toggleCategory('le30');
    expect(useAppStore.getState().selectedCategory).toBe('le30');
    useAppStore.getState().toggleCategory('le30');
    expect(useAppStore.getState().selectedCategory).toBeNull();
  });
});

describe('area in the URL', () => {
  const polygon = { type: 'Polygon' as const, coordinates: [RING] };

  it('encodes a drawn polygon to a short parameter and omits it for the district', () => {
    expect(searchForArea({ kind: 'drawn', geometry: polygon })).toBe(
      '?area=2.16,41.39,2.17,41.39,2.17,41.397',
    );
    expect(searchForArea(districtArea())).toBe('');
  });

  it('round-trips through the URL, closing the ring again', () => {
    const search = searchForArea({ kind: 'drawn', geometry: polygon });
    expect(areaFromSearch(search)).toEqual({ kind: 'drawn', geometry: polygon });
  });

  it('rounds to 5 decimals, the precision the API serves', () => {
    const precise = {
      type: 'Polygon' as const,
      coordinates: [
        [
          [2.1600004999, 41.39],
          [2.17, 41.39],
          [2.17, 41.397],
          [2.1600004999, 41.39],
        ],
      ],
    };
    expect(searchForArea({ kind: 'drawn', geometry: precise })).toContain('2.16,41.39');
  });

  it.each([
    ['', 'no parameter'],
    ['?area=', 'empty'],
    ['?area=2.16,41.39,2.17,41.39', 'too few points for a polygon'],
    ['?area=2.16,41.39,2.17,41.39,2.17', 'odd number of coordinates'],
    ['?area=2.16,41.39,2.17,nope,2.17,41.397', 'not a number'],
    ['?area=200,41.39,2.17,41.39,2.17,41.397', 'out of range'],
  ])('falls back to the district for %s (%s)', (search) => {
    expect(areaFromSearch(search)).toEqual(districtArea());
  });
});
