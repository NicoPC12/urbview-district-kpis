/**
 * The single client store. The map and the dashboard are two views of it (CLAUDE.md §7).
 *
 * Only *selection* lives here: which area, which KPI is active, which category or feature
 * is highlighted, whether the user is drawing. KPI numbers never do — they live in TanStack
 * Query keyed by `area`, so there is exactly one copy of every number on screen.
 */

import type { Polygon } from 'geojson';
import { create } from 'zustand';

import { areaFromSearch } from '@/lib/areaUrl';

/** The whole district, or a polygon the user drew (EPSG:4326). */
export type AreaSelection =
  { kind: 'district'; slug: string } | { kind: 'drawn'; geometry: Polygon };

/** In `draw` mode feature clicks are off, so terra-draw alone consumes the click. */
export type MapMode = 'inspect' | 'draw';

/** The district the app opens on. The API's district catalogue confirms it exists. */
export const DEFAULT_DISTRICT_SLUG = 'eixample';

export interface AppState {
  /** Drives the query key, and therefore every number on screen. */
  area: AreaSelection;
  /** Which KPI's layer, legend and chart are shown; one at a time. */
  activeKpiKey: string | null;
  /** Dashboard → map: a breakdown/legend category to emphasise on the map. */
  selectedCategory: string | null;
  /** Map → dashboard: the GERS id of a clicked feature whose contribution is shown. */
  selectedFeatureId: string | null;
  mode: MapMode;

  setArea: (area: AreaSelection) => void;
  /** Back to the whole district in one action; both views follow. */
  clearArea: () => void;
  setActiveKpi: (key: string | null) => void;
  /** Click a category to emphasise it; click it again to clear. */
  toggleCategory: (category: string) => void;
  selectFeature: (id: string | null) => void;
  setMode: (mode: MapMode) => void;
}

export const districtArea = (slug = DEFAULT_DISTRICT_SLUG): AreaSelection => ({
  kind: 'district',
  slug,
});

/**
 * The area the app opens on: whatever `?area=` names, else the district.
 *
 * Read here rather than in an effect. Effects of one commit all see the area from the render
 * that queued them, so a hook that read the URL into the store would still leave the
 * URL-writing effect holding this default — and it would push that over the incoming
 * parameter. See `features/area/useAreaUrl`.
 */
function initialArea(): AreaSelection {
  return areaFromSearch(window.location.search) ?? districtArea();
}

export const useAppStore = create<AppState>()((set) => ({
  area: initialArea(),
  activeKpiKey: null,
  selectedCategory: null,
  selectedFeatureId: null,
  mode: 'inspect',

  // A new area has new features: any highlight would point at something no longer shown.
  setArea: (area) => {
    set({ area, selectedFeatureId: null, selectedCategory: null, mode: 'inspect' });
  },
  clearArea: () => {
    set({ area: districtArea(), selectedFeatureId: null, selectedCategory: null, mode: 'inspect' });
  },
  setActiveKpi: (key) => {
    set({ activeKpiKey: key, selectedCategory: null, selectedFeatureId: null });
  },
  toggleCategory: (category) => {
    set((s) => ({ selectedCategory: s.selectedCategory === category ? null : category }));
  },
  selectFeature: (id) => {
    set({ selectedFeatureId: id });
  },
  setMode: (mode) => {
    set({ mode });
  },
}));
