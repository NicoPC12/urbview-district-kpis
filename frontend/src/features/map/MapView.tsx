/**
 * The map half of the page. Talks to the dashboard only through the store.
 *
 * Reads: the area (to fetch the same response the dashboard shows — TanStack dedupes it),
 * the active KPI, the selection and the mode. Writes: `setArea` (drawing), `selectFeature`
 * (clicking a feature), `setMode` and `clearArea` (the buttons).
 */

import type { MapLayerMouseEvent, MapMouseEvent } from 'maplibre-gl';
import { useEffect, useMemo } from 'react';

import { useDistricts, useKpis } from '@/api/useKpis';
import { districtArea, useAppStore } from '@/state/store';

import { inScope } from './layers';
import { useDistrictOutline } from './useDistrictOutline';
import { raiseAreaLayers, useKpiLayers } from './useKpiLayers';
import { useMap } from './useMap';

/** MapLibre canvas plus the draw controls overlaid on it. */
export function MapView() {
  const { containerRef, map } = useMap();
  const area = useAppStore((s) => s.area);
  const activeKpiKey = useAppStore((s) => s.activeKpiKey);
  const selectedCategory = useAppStore((s) => s.selectedCategory);
  const selectedFeatureId = useAppStore((s) => s.selectedFeatureId);
  const mode = useAppStore((s) => s.mode);
  const selectFeature = useAppStore((s) => s.selectFeature);

  const districts = useDistricts();
  const district = districts.data?.find((d) => area.kind !== 'district' || d.slug === area.slug);
  useDistrictOutline(map, district);

  const areaQuery = useKpis(area);
  // Pitfall 2: with a drawing active, the district response stays underneath, dimmed.
  const contextQuery = useKpis(districtArea());
  const drawn = area.kind === 'drawn';

  const highlight = useMemo(
    () => ({ selectedCategory, selectedFeatureId }),
    [selectedCategory, selectedFeatureId],
  );
  useKpiLayers({
    map,
    scope: 'context',
    response: drawn ? contextQuery.data : undefined,
    activeKpiKey,
    highlight,
  });
  useKpiLayers({ map, scope: 'area', response: areaQuery.data, activeKpiKey, highlight });
  useEffect(() => {
    if (map !== null) raiseAreaLayers(map);
  }, [map, areaQuery.data, contextQuery.data, activeKpiKey, drawn]);

  // Map → dashboard: click a feature of the area scope. Off while drawing (Pitfall: two
  // handlers on one click).
  useEffect(() => {
    if (map === null || mode === 'draw') return;
    const interactive = (): string[] =>
      map
        .getStyle()
        .layers.map((l) => l.id)
        .filter((id) => inScope('area', id) && !id.includes(':selected-'));
    const onClick = (event: MapMouseEvent): void => {
      const layers = interactive();
      if (layers.length === 0) return;
      const hit = map.queryRenderedFeatures(event.point, { layers })[0];
      const id: unknown = hit?.properties.id;
      selectFeature(typeof id === 'string' ? id : null);
    };
    const onMove = (event: MapLayerMouseEvent): void => {
      const layers = interactive();
      const over =
        layers.length > 0 && map.queryRenderedFeatures(event.point, { layers }).length > 0;
      map.getCanvas().style.cursor = over ? 'pointer' : '';
    };
    map.on('click', onClick);
    map.on('mousemove', onMove);
    return () => {
      map.off('click', onClick);
      map.off('mousemove', onMove);
      map.getCanvas().style.cursor = '';
    };
  }, [map, mode, selectFeature, activeKpiKey]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" data-testid="map-canvas" />
    </div>
  );
}
