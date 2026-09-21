/**
 * Area selection logic shared by the map (which produces areas) and the dashboard (which
 * describes them). Pure functions: no store, no map, so they run in jsdom.
 */

import type { Polygon } from 'geojson';

import type { KpiRequestRequest } from '@/api/schema.gen';
import type { AreaSelection } from '@/state/store';

/** The API request body for an area selection. */
export function areaToRequest(area: AreaSelection): KpiRequestRequest {
  switch (area.kind) {
    case 'district':
      return { district: area.slug };
    case 'drawn':
      return { polygon: { type: 'Polygon', coordinates: area.geometry.coordinates } };
  }
}

/** Result of finishing a drawing: an area to select, or why the shape cannot be one. */
export type DrawResult = { ok: true; area: AreaSelection } | { ok: false; reason: string };

function isPosition(value: unknown): value is [number, number] {
  return (
    Array.isArray(value) &&
    value.length >= 2 &&
    typeof value[0] === 'number' &&
    Number.isFinite(value[0]) &&
    typeof value[1] === 'number' &&
    Number.isFinite(value[1]) &&
    Math.abs(value[0]) <= 180 &&
    Math.abs(value[1]) <= 90
  );
}

/**
 * Turn whatever the draw tool finished into an `AreaSelection`.
 *
 * Structural checks only (one closed ring of at least four finite lon/lat positions); the
 * backend owns validity, size and vertex caps and answers 422 with a reason the UI shows.
 */
export function finishDrawing(geometry: unknown): DrawResult {
  if (typeof geometry !== 'object' || geometry === null) {
    return { ok: false, reason: 'No geometry was drawn.' };
  }
  const { type, coordinates } = geometry as { type?: unknown; coordinates?: unknown };
  if (type !== 'Polygon' || !Array.isArray(coordinates)) {
    return { ok: false, reason: 'Only a polygon can be an area.' };
  }
  const ring: unknown = coordinates[0];
  if (coordinates.length !== 1 || !Array.isArray(ring) || !ring.every(isPosition)) {
    return { ok: false, reason: 'The polygon must be one ring of [lon, lat] positions.' };
  }
  if (ring.length < 4) {
    return { ok: false, reason: 'A polygon needs at least three distinct points.' };
  }
  const first = ring[0];
  const last = ring[ring.length - 1];
  if (first?.[0] !== last?.[0] || first?.[1] !== last?.[1]) {
    return { ok: false, reason: 'The polygon ring is not closed.' };
  }
  const polygon: Polygon = { type: 'Polygon', coordinates: [ring.map(([x, y]) => [x, y])] };
  return { ok: true, area: { kind: 'drawn', geometry: polygon } };
}
