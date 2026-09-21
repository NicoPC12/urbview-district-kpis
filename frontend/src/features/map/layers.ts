/**
 * Pure builders for MapLibre sources, layers and highlight expressions.
 *
 * No map access here: everything is a function of (KPI layer, legend, selection), so the
 * highlighting logic — the dashboard → map half of the bidirectional interaction — is unit
 * tested without WebGL. `useKpiLayers` applies the results to the map.
 */

import type { ExpressionSpecification, FilterSpecification, LayerSpecification } from 'maplibre-gl';

import type { LegendItem } from '@/api/schema.gen';

/** `area`: the selected area's features; `context`: the district, dimmed underneath. */
export type LayerScope = 'area' | 'context';

/** What the store contributes to the paint of a layer. */
export interface HighlightState {
  selectedCategory: string | null;
  selectedFeatureId: string | null;
}

/** Colour for a category the legend does not name (matches the backend's DEFAULT_COLOR). */
export const FALLBACK_COLOR = '#94a3b8';
/** Outline colour of the selected feature. Not a KPI colour: a neutral ink. */
export const SELECTED_COLOR = '#0f172a';

const DIM_OPACITY = 0.2;
const CONTEXT_OPACITY = 0.35;

export const sourceId = (scope: LayerScope, layerId: string): string => `${scope}:${layerId}`;

/** The map layer ids one KPI layer expands to (one per geometry type, plus selection). */
export function layerIds(scope: LayerScope, layerId: string): string[] {
  const base = sourceId(scope, layerId);
  return [
    `${base}:fill`,
    `${base}:line`,
    `${base}:circle`,
    `${base}:selected-line`,
    `${base}:selected-circle`,
  ];
}

/** Whether a map layer/source id belongs to a scope (for removal of stale layers). */
export const inScope = (scope: LayerScope, id: string): boolean => id.startsWith(`${scope}:`);

/** `['match', category, key, color, ..., fallback]` from the legend of one KPI. */
export function colorExpression(legend: LegendItem[]): ExpressionSpecification | string {
  if (legend.length === 0) return FALLBACK_COLOR;
  const pairs = legend.flatMap((item) => [item.key, item.color]);
  // MapLibre types `match` as alternating (label, output) tuples, which a flatMap cannot
  // express; the shape is exactly that, so the cast is a typing limit, not a guess.
  return [
    'match',
    ['get', 'category'],
    ...pairs,
    FALLBACK_COLOR,
  ] as unknown as ExpressionSpecification;
}

/**
 * Opacity that emphasises the selected category and dims the rest. With nothing selected,
 * every feature gets `base`. This is the whole of "clicking a chart bar filters the map".
 */
export function emphasisExpression(
  selectedCategory: string | null,
  base: number,
): ExpressionSpecification | number {
  if (selectedCategory === null) return base;
  return ['case', ['==', ['get', 'category'], selectedCategory], base, base * DIM_OPACITY];
}

/** Filter that keeps only the selected feature (GERS id promoted into `properties.id`). */
export function selectedFilter(selectedFeatureId: string | null): ExpressionSpecification {
  return ['==', ['get', 'id'], selectedFeatureId ?? ''];
}

/** Every layer for one KPI layer in one scope, in draw order (fills under lines under points). */
export function layerSpecs(
  scope: LayerScope,
  layerId: string,
  legend: LegendItem[],
  highlight: HighlightState,
): LayerSpecification[] {
  const source = sourceId(scope, layerId);
  const [fill, line, circle, selectedLine, selectedCircle] = layerIds(scope, layerId) as [
    string,
    string,
    string,
    string,
    string,
  ];
  const color = colorExpression(legend);
  const base = scope === 'context' ? CONTEXT_OPACITY : 1;
  const opacity = scope === 'context' ? base : emphasisExpression(highlight.selectedCategory, base);
  const selectedId = scope === 'area' ? highlight.selectedFeatureId : null;

  return [
    {
      id: fill,
      type: 'fill',
      source,
      filter: ['==', ['geometry-type'], 'Polygon'],
      paint: {
        'fill-color': color,
        'fill-opacity': typeof opacity === 'number' ? opacity * 0.35 : ['*', opacity, 0.35],
      },
    },
    {
      id: line,
      type: 'line',
      source,
      filter: [
        'any',
        ['==', ['geometry-type'], 'LineString'],
        ['==', ['geometry-type'], 'Polygon'],
      ],
      paint: {
        'line-color': color,
        'line-opacity': opacity,
        'line-width': scope === 'context' ? 1.5 : 2.5,
      },
    },
    {
      id: circle,
      type: 'circle',
      source,
      filter: ['==', ['geometry-type'], 'Point'],
      paint: {
        'circle-color': color,
        'circle-opacity': opacity,
        'circle-radius': scope === 'context' ? 2.5 : 4,
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': scope === 'context' ? 0 : 1,
      },
    },
    {
      id: selectedLine,
      type: 'line',
      source,
      filter: ['all', ['!=', ['geometry-type'], 'Point'], selectedFilter(selectedId)],
      paint: { 'line-color': SELECTED_COLOR, 'line-width': 6, 'line-opacity': 0.9 },
    },
    {
      id: selectedCircle,
      type: 'circle',
      source,
      filter: ['all', ['==', ['geometry-type'], 'Point'], selectedFilter(selectedId)],
      paint: {
        'circle-color': 'rgba(0,0,0,0)',
        'circle-radius': 9,
        'circle-stroke-color': SELECTED_COLOR,
        'circle-stroke-width': 3,
      },
    },
  ];
}

/** Paint properties that change with the selection, keyed by layer id, without re-adding. */
export function highlightPaint(
  scope: LayerScope,
  layerId: string,
  highlight: HighlightState,
): {
  paint: Record<string, [string, ExpressionSpecification | number]>;
  filters: Record<string, FilterSpecification>;
} {
  const [fill, line, circle, selectedLine, selectedCircle] = layerIds(scope, layerId) as [
    string,
    string,
    string,
    string,
    string,
  ];
  if (scope === 'context') return { paint: {}, filters: {} };
  const opacity = emphasisExpression(highlight.selectedCategory, 1);
  return {
    paint: {
      [fill]: ['fill-opacity', typeof opacity === 'number' ? opacity * 0.35 : ['*', opacity, 0.35]],
      [line]: ['line-opacity', opacity],
      [circle]: ['circle-opacity', opacity],
    },
    filters: {
      [selectedLine]: [
        'all',
        ['!=', ['geometry-type'], 'Point'],
        selectedFilter(highlight.selectedFeatureId),
      ],
      [selectedCircle]: [
        'all',
        ['==', ['geometry-type'], 'Point'],
        selectedFilter(highlight.selectedFeatureId),
      ],
    },
  };
}
