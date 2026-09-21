/**
 * One MapLibre instance, created imperatively, handed out only after its style has loaded.
 *
 * React StrictMode mounts, unmounts and remounts every effect in development; the effect
 * below creates the map and removes it on cleanup, so the second mount gets a fresh map
 * and there is never a second one alive on the same container. Consumers receive `null`
 * until the `load` event, so no source or layer is ever added before the style exists.
 */

import maplibregl, { type Map as MapLibreMap } from 'maplibre-gl';
import { useEffect, useRef, useState, type RefObject } from 'react';

/**
 * Keyless vector basemap. Cartographic context only: no KPI reads it (NOTES.md). Override
 * with `VITE_BASEMAP_STYLE_URL` for an offline or self-hosted style.
 */
export const BASEMAP_STYLE_URL: string =
  import.meta.env.VITE_BASEMAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/positron';

/** Barcelona, Eixample; overwritten by the district's bounds as soon as they load. */
const INITIAL_CENTER: [number, number] = [2.164, 41.393];
const INITIAL_ZOOM = 13.5;

export interface UseMapResult {
  containerRef: RefObject<HTMLDivElement>;
  /** The map, once its style has loaded; `null` before that. */
  map: MapLibreMap | null;
}

/** Create the map on mount and expose it after `load`. */
export function useMap(): UseMapResult {
  const containerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<MapLibreMap | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (container === null) return;
    const instance = new maplibregl.Map({
      container,
      style: BASEMAP_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      attributionControl: { compact: true },
    });
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
    instance.on('load', () => {
      setMap(instance);
    });
    return () => {
      setMap(null);
      instance.remove();
    };
  }, []);

  return { containerRef, map };
}
