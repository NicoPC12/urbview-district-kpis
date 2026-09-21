/**
 * The one place colours are written down on the frontend.
 *
 * Map categories are coloured by the API legend. Band pills use this single-hue ramp,
 * never a traffic light: a red card would read as "dangerous", which no KPI here can
 * support (NOTES.md "Palette"). Lighter = worse, darker = better, ordered by the KPI's
 * `lower_is_better`.
 */

/** Sequential blue ramp, light to dark (Tailwind sky-100 … sky-900). */
export const BAND_RAMP: readonly string[] = [
  '#e0f2fe',
  '#bae6fd',
  '#7dd3fc',
  '#0284c7',
  '#075985',
  '#0c4a6e',
];

/** Text colour that stays legible on each ramp step (dark on light, white on dark). */
export const BAND_TEXT_DARK = '#0c4a6e';
export const BAND_TEXT_LIGHT = '#ffffff';

/** Ramp steps light enough for dark text. */
export const LIGHT_STEPS = 3;

/** Neutral ink for the selected feature's outline and emphasis. */
export const INK = '#0f172a';

/** Colour for a map category the legend does not name (matches the backend's DEFAULT_COLOR). */
export const FALLBACK_COLOR = '#94a3b8';

/** Outline colour of the selected feature on the map. */
export const SELECTED_COLOR = INK;

/** The district outline (dashed). */
export const OUTLINE_COLOR = '#334155';

/** Halo around area points so they read on any basemap colour. */
export const POINT_HALO = '#ffffff';
/** Fallback when a ramp index is out of range (should never render). */
export const BLACK = '#000000';
