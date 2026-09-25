/**
 * What one map feature contributes to its KPI — the map → dashboard half of the
 * bidirectional interaction, computed from the already-loaded layer, never by a request.
 *
 * One pure function per KPI, keyed by KPI key. Adding a KPI with a new kind of feature means
 * adding one entry here; a KPI without an entry falls back to naming the feature.
 */

import type { KpiResponse, LegendItem } from '@/api/schema.gen';
import { formatInt, formatMetres, formatShare } from '@/lib/format';

type ApiFeature = KpiResponse['layers']['vectors'][number]['data']['features'][number];
type ApiLayer = KpiResponse['layers']['vectors'][number];

export interface Contribution {
  /** The feature's name when mapped, otherwise its category label. */
  title: string;
  /** One sentence with at least one computed number. */
  detail: string;
  layerId: string;
}

interface Located {
  feature: ApiFeature;
  layer: ApiLayer;
}

function locate(layers: ApiLayer[], featureId: string): Located | null {
  for (const layer of layers) {
    const feature = layer.data.features.find((f) => f.id === featureId);
    if (feature !== undefined) return { feature, layer };
  }
  return null;
}

function categoryLabel(legend: LegendItem[], kpiKey: string, category: string): string {
  // A KPI with a breakdown puts only its breakdown keys in the legend, so a single-category
  // layer (`green_space`, `tree`) has no entry; humanise the key rather than print it raw.
  const item = legend.find((i) => i.kpi_key === kpiKey && i.key === category);
  return item?.label ?? category.replace(/_/g, ' ');
}

function shareOfLength(layer: ApiLayer, feature: ApiFeature): string {
  const total = layer.data.features.reduce((sum, f) => sum + (f.properties.length_m ?? 0), 0);
  const own = feature.properties.length_m ?? 0;
  return total > 0 ? formatShare(own / total) : '0 %';
}

function countOf(layer: ApiLayer): string {
  return formatInt(layer.data.features.length);
}

interface Naming {
  /** The feature's name, or its category label when unnamed. */
  title: string;
  /** Human label of a category key from the legend. */
  label: (category: string) => string;
}

type Describer = (located: Located, naming: Naming) => string;

/** Sentence builders keyed by KPI key. Every sentence carries a computed number. */
const DESCRIBERS: Record<string, Describer> = {
  low_speed_street_share: ({ feature, layer }, { title, label }) =>
    `${title}: ${formatMetres(feature.properties.length_m ?? 0)} of carriageway posted ${label(feature.properties.category)}, ${shareOfLength(layer, feature)} of the carriageway in this area.`,
  pedestrian_network_share: ({ feature, layer }, { title, label }) =>
    `${title}: ${formatMetres(feature.properties.length_m ?? 0)} of ${label(feature.properties.category)}, ${shareOfLength(layer, feature)} of the mapped network in this area.`,
  crossing_density: ({ layer }, { title }) =>
    `${title}: 1 of ${countOf(layer)} crossings in this area.`,
  street_tree_density: ({ layer }, { title }) =>
    `${title}: 1 of ${countOf(layer)} mapped trees in this area.`,
  green_space_distance_p50: ({ feature, layer }, { title }) => {
    if (feature.properties.area_ha !== undefined) {
      return `${title}: ${String(feature.properties.area_ha)} ha, the nearest green space of at least 0.5 ha for buildings in this area.`;
    }
    const distance = feature.properties.distance_m ?? 0;
    const nearer = layer.data.features.filter(
      (f) => (f.properties.distance_m ?? Infinity) < distance,
    ).length;
    const share = layer.data.features.length > 0 ? nearer / layer.data.features.length : 0;
    return `${title}: ${formatMetres(distance)} to the nearest green space of at least 0.5 ha — further than ${formatShare(share)} of the buildings in this area.`;
  },
};

/**
 * Describe the selected feature's contribution to the active KPI, from loaded data only.
 *
 * Returns `null` when the feature is not in any of the KPI's layers (e.g. it belongs to a
 * KPI that is no longer active, or the area changed).
 */
export function describeContribution(
  response: KpiResponse,
  kpiKey: string,
  featureId: string,
): Contribution | null {
  const kpi = response.kpis.find((k) => k.key === kpiKey);
  if (kpi === undefined) return null;
  const layers = response.layers.vectors.filter((l) => l.kpi_key === kpiKey);
  const located = locate(layers, featureId);
  if (located === null) return null;
  const { feature, layer } = located;
  const label = (category: string): string =>
    categoryLabel(response.legend.items, kpi.key, category);
  const title = feature.properties.name ?? label(feature.properties.category);
  const describe = DESCRIBERS[kpiKey];
  const detail =
    describe === undefined
      ? `${title} is one of ${countOf(layer)} features behind this KPI.`
      : describe(located, { title, label });
  return { title, detail, layerId: layer.id };
}
