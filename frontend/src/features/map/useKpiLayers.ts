/**
 * Keep the map's sources and layers in step with the active KPI and the selection.
 *
 * Two effects on purpose. The *data* effect runs when the response or the active KPI
 * changes: it (re)creates sources and layers for that KPI in a scope. The *highlight*
 * effect runs when the selection changes: it only touches paint properties and filters, so
 * clicking a chart bar never re-parses megabytes of GeoJSON (CLAUDE.md §7: never refetch,
 * never reload, to highlight).
 */

import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl';
import { useEffect } from 'react';

import { PROMOTE_ID, toFeatureCollection } from '@/api/geojson';
import type { KpiResponse } from '@/api/schema.gen';

import {
  highlightPaint,
  inScope,
  layerIds,
  layerSpecs,
  sourceId,
  type HighlightState,
  type LayerScope,
} from './layers';

interface UseKpiLayersOptions {
  map: MapLibreMap | null;
  scope: LayerScope;
  /** The response whose layers this scope shows; `undefined` clears the scope. */
  response: KpiResponse | undefined;
  activeKpiKey: string | null;
  highlight: HighlightState;
}

/** Remove every layer and source of a scope that is not in `keep`. */
function removeStale(map: MapLibreMap, scope: LayerScope, keep: Set<string>): void {
  for (const layer of map.getStyle().layers) {
    if (inScope(scope, layer.id) && !keep.has(layer.id)) map.removeLayer(layer.id);
  }
  for (const source of Object.keys(map.getStyle().sources)) {
    if (inScope(scope, source) && !keep.has(source)) map.removeSource(source);
  }
}

/** Sync one scope's sources and layers with the active KPI's layers. */
export function useKpiLayers({
  map,
  scope,
  response,
  activeKpiKey,
  highlight,
}: UseKpiLayersOptions): void {
  useEffect(() => {
    if (map === null) return;
    const layers = response?.layers.vectors.filter((l) => l.kpi_key === activeKpiKey) ?? [];
    const legend = response?.legend.items.filter((i) => i.kpi_key === activeKpiKey) ?? [];
    const keep = new Set<string>();
    for (const layer of layers) {
      const id = sourceId(scope, layer.id);
      keep.add(id);
      for (const layerId of layerIds(scope, layer.id)) keep.add(layerId);
      const data = toFeatureCollection(layer.data);
      const existing = map.getSource<GeoJSONSource>(id);
      if (existing === undefined) {
        map.addSource(id, { type: 'geojson', data, promoteId: PROMOTE_ID });
      } else {
        existing.setData(data);
      }
      for (const spec of layerSpecs(scope, layer.id, legend, highlight)) {
        if (map.getLayer(spec.id) === undefined) map.addLayer(spec);
      }
    }
    removeStale(map, scope, keep);
    // The highlight state is applied by the effect below; listing it here would re-parse data.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, scope, response, activeKpiKey]);

  useEffect(() => {
    if (map === null || response === undefined) return;
    for (const layer of response.layers.vectors) {
      if (layer.kpi_key !== activeKpiKey) continue;
      const { paint, filters } = highlightPaint(scope, layer.id, highlight);
      for (const [layerId, [property, value]] of Object.entries(paint)) {
        if (map.getLayer(layerId) !== undefined) map.setPaintProperty(layerId, property, value);
      }
      for (const [layerId, filter] of Object.entries(filters)) {
        if (map.getLayer(layerId) !== undefined) map.setFilter(layerId, filter);
      }
    }
  }, [map, scope, response, activeKpiKey, highlight]);
}

/** terra-draw's MapLibre adapter prefixes every layer it adds with this. */
const DRAW_LAYER_PREFIX = 'td';

/**
 * Draw order: context under area under the drawing tool. Layers are added as responses
 * arrive, in no guaranteed order, so re-stack after every change.
 */
export function raiseAreaLayers(map: MapLibreMap): void {
  const ids = map.getStyle().layers.map((l) => l.id);
  for (const id of ids) if (inScope('area', id)) map.moveLayer(id);
  for (const id of ids) if (id.startsWith(DRAW_LAYER_PREFIX)) map.moveLayer(id);
}
