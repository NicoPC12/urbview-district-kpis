/**
 * The one place where the API's GeoJSON is narrowed to `@types/geojson`.
 *
 * OpenAPI cannot express GeoJSON's recursive coordinate arrays, so `schema.gen.ts` types a
 * geometry as `{ type: <enum>; coordinates: unknown[] }`. MapLibre and every geometry helper
 * want `GeoJSON.Geometry`. This adapter is the documented, single point of trust: it checks
 * the discriminant the schema does guarantee and the array shape, and everything downstream
 * works with `@types/geojson` types. Nothing else in the codebase casts geometry.
 */

import type {
  Feature,
  FeatureCollection,
  Geometry,
  LineString,
  MultiLineString,
  MultiPoint,
  MultiPolygon,
  Point,
  Polygon,
} from 'geojson';

import type { components } from './schema.gen';

type ApiGeometry = components['schemas']['Feature']['geometry'];
type ApiFeature = components['schemas']['Feature'];
type ApiFeatureCollection = components['schemas']['FeatureCollection'];

/**
 * Feature properties as the API declares them, plus the GERS id copied in as `id`.
 *
 * MapLibre only honours numeric feature ids for `feature-state`; a UUID string id is
 * dropped silently. Every source is therefore created with `promoteId: 'id'`, which reads
 * the id back from this property. See `PROMOTE_ID`.
 */
export type FeatureProperties = components['schemas']['FeatureProperties'] & { id: string };

/** The `promoteId` every GeoJSON source must be created with (Pitfall 1). */
export const PROMOTE_ID = 'id';

/** A GeoJSON position `[lon, lat]` (a third element is tolerated and ignored). */
function isPosition(value: unknown): value is [number, number] {
  return (
    Array.isArray(value) &&
    value.length >= 2 &&
    typeof value[0] === 'number' &&
    typeof value[1] === 'number'
  );
}

function isPositionArray(value: unknown): value is [number, number][] {
  return Array.isArray(value) && value.every(isPosition);
}

function isRingArray(value: unknown): value is [number, number][][] {
  return Array.isArray(value) && value.every(isPositionArray);
}

function isPolygonArray(value: unknown): value is [number, number][][][] {
  return Array.isArray(value) && value.every(isRingArray);
}

/**
 * Narrow an API geometry to `GeoJSON.Geometry`.
 *
 * @throws Error when the coordinates do not have the nesting the `type` promises. The
 *   backend rounds and serialises geometry itself, so this only fires on a broken contract.
 */
export function toGeometry(geometry: ApiGeometry): Geometry {
  const { type, coordinates } = geometry;
  switch (type) {
    case 'Point':
      if (isPosition(coordinates)) return { type, coordinates } satisfies Point;
      break;
    case 'MultiPoint':
      if (isPositionArray(coordinates)) return { type, coordinates } satisfies MultiPoint;
      break;
    case 'LineString':
      if (isPositionArray(coordinates)) return { type, coordinates } satisfies LineString;
      break;
    case 'MultiLineString':
      if (isRingArray(coordinates)) return { type, coordinates } satisfies MultiLineString;
      break;
    case 'Polygon':
      if (isRingArray(coordinates)) return { type, coordinates } satisfies Polygon;
      break;
    case 'MultiPolygon':
      if (isPolygonArray(coordinates)) return { type, coordinates } satisfies MultiPolygon;
      break;
  }
  throw new Error(`GeoJSON ${type} with malformed coordinates`);
}

/** Narrow one API feature; the GERS id is kept as `id` and copied into `properties.id`. */
export function toFeature(feature: ApiFeature): Feature<Geometry, FeatureProperties> {
  return {
    type: 'Feature',
    id: feature.id,
    geometry: toGeometry(feature.geometry),
    properties: { ...feature.properties, id: feature.id },
  };
}

/** Narrow a whole layer. */
export function toFeatureCollection(
  collection: ApiFeatureCollection,
): FeatureCollection<Geometry, FeatureProperties> {
  return { type: 'FeatureCollection', features: collection.features.map(toFeature) };
}
