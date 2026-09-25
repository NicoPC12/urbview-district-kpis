/**
 * The area codec for `?area=`, so a view can be linked, bookmarked and screenshotted.
 *
 * Encoding: `?area=<lon>,<lat>,<lon>,<lat>,…` with coordinates rounded to 5 decimals (~1 m,
 * the precision the API serves) and the closing point dropped. A block-sized polygon is
 * ~90 characters — short enough to read and to paste into a deck. No `area` parameter means
 * the whole district, so the plain URL stays clean.
 *
 * It lives in `lib/` and imports only the *type* of an area selection, which is erased at
 * runtime: `state/store` initialises itself from the URL, and a value import here would make
 * that a circular one. The hook that wires this to history is `features/area/useAreaUrl`.
 */

import type { Polygon } from 'geojson';

import type { AreaSelection } from '@/state/store';

export const AREA_PARAM = 'area';

/** Coordinate precision in the URL; matches the API's 5 decimals. */
const DECIMALS = 5;

const round = (n: number): number => Number(n.toFixed(DECIMALS));

/** `?area=…` value for an area, or `null` for the district (the parameter is then omitted). */
export function encodeArea(area: AreaSelection): string | null {
  if (area.kind === 'district') return null;
  const ring = area.geometry.coordinates[0] ?? [];
  // The ring is closed; the last point repeats the first, so it is not encoded.
  return ring
    .slice(0, -1)
    .map(([lon, lat]) => `${String(round(lon ?? 0))},${String(round(lat ?? 0))}`)
    .join(',');
}

/**
 * Parse an `?area=` value into a drawn selection.
 *
 * Returns `null` for a missing, empty or malformed value — a broken link should open the
 * app on the district, not an error page. The caller supplies that fallback. The backend
 * still validates the polygon it is sent.
 */
export function decodeArea(value: string | null): AreaSelection | null {
  if (value === null || value.trim() === '') return null;
  const numbers = value.split(',').map(Number);
  if (numbers.length < 6 || numbers.length % 2 !== 0 || numbers.some((n) => !Number.isFinite(n))) {
    return null;
  }
  const ring: [number, number][] = [];
  for (let i = 0; i < numbers.length; i += 2) {
    const lon = numbers[i];
    const lat = numbers[i + 1];
    if (lon === undefined || lat === undefined || Math.abs(lon) > 180 || Math.abs(lat) > 90) {
      return null;
    }
    ring.push([lon, lat]);
  }
  const first = ring[0];
  if (first === undefined) return null;
  const geometry: Polygon = { type: 'Polygon', coordinates: [[...ring, first]] };
  return { kind: 'drawn', geometry };
}

/** The area a URL's search string selects, or `null` when it names none. */
export function areaFromSearch(search: string): AreaSelection | null {
  return decodeArea(new URLSearchParams(search).get(AREA_PARAM));
}

/** The search string for an area, `''` for the district. */
export function searchForArea(area: AreaSelection): string {
  const encoded = encodeArea(area);
  return encoded === null ? '' : `?${AREA_PARAM}=${encoded}`;
}

/** `pathname + search` for an area, i.e. what the address bar should read. */
export function urlForArea(area: AreaSelection): string {
  return `${window.location.pathname}${searchForArea(area)}`;
}
