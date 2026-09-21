/**
 * Draw the district outline and fit the map to it once, when both map and outline exist.
 */

import type { GeoJSONSource, LngLatBoundsLike, Map as MapLibreMap } from 'maplibre-gl';
import { useEffect, useRef } from 'react';

import { toGeometry } from '@/api/geojson';
import type { District } from '@/api/schema.gen';
import { OUTLINE_COLOR } from '@/lib/theme';

const SOURCE = 'district-outline';

/** Add the outline source/layers and fit bounds on the first render of each district. */
export function useDistrictOutline(map: MapLibreMap | null, district: District | undefined): void {
  const fittedSlug = useRef<string | null>(null);

  useEffect(() => {
    if (map === null || district === undefined) return;
    const data = {
      type: 'Feature' as const,
      properties: {},
      geometry: toGeometry(district.geometry),
    };
    const existing = map.getSource<GeoJSONSource>(SOURCE);
    if (existing === undefined) {
      map.addSource(SOURCE, { type: 'geojson', data });
      map.addLayer({
        id: `${SOURCE}:line`,
        type: 'line',
        source: SOURCE,
        paint: { 'line-color': OUTLINE_COLOR, 'line-width': 2, 'line-dasharray': [3, 2] },
      });
    } else {
      existing.setData(data);
    }
    if (fittedSlug.current !== district.slug) {
      fittedSlug.current = district.slug;
      const [xmin, ymin, xmax, ymax] = district.bbox;
      if (xmin !== undefined && ymin !== undefined && xmax !== undefined && ymax !== undefined) {
        const bounds: LngLatBoundsLike = [
          [xmin, ymin],
          [xmax, ymax],
        ];
        map.fitBounds(bounds, { padding: 24, duration: 0 });
      }
    }
  }, [map, district]);
}
