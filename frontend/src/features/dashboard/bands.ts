/**
 * Band ordering and colouring — pure, so the "no traffic light" rule is a tested fact.
 */

import type { Kpi } from '@/api/schema.gen';
import { BAND_RAMP, BAND_TEXT_DARK, BAND_TEXT_LIGHT, BLACK, LIGHT_STEPS } from '@/lib/theme';

export interface BandStyle {
  /** 0 = worst band, `total - 1` = best, whatever direction the KPI runs. */
  rank: number;
  total: number;
  background: string;
  color: string;
}

/** Ramp steps for `total` bands, evenly spread from light (worst) to dark (best). */
export function rampFor(total: number): string[] {
  if (total <= 1) return [BAND_RAMP[BAND_RAMP.length - 1] ?? BLACK];
  return Array.from({ length: total }, (_, i) => {
    const step = Math.round((i * (BAND_RAMP.length - 1)) / (total - 1));
    return BAND_RAMP[step] ?? BLACK;
  });
}

/**
 * Style for a KPI's current band. Bands come from the API in ascending value order; with
 * `lower_is_better` the first band is the best, otherwise the last is.
 */
export function bandStyle(kpi: Pick<Kpi, 'bands' | 'band' | 'lower_is_better'>): BandStyle | null {
  const index = kpi.bands.findIndex((b) => b.label === kpi.band);
  if (kpi.band === null || index === -1) return null;
  const total = kpi.bands.length;
  const rank = kpi.lower_is_better ? total - 1 - index : index;
  const ramp = rampFor(total);
  const step = Math.round((rank * (BAND_RAMP.length - 1)) / Math.max(total - 1, 1));
  return {
    rank,
    total,
    background: ramp[rank] ?? BLACK,
    color: step < LIGHT_STEPS ? BAND_TEXT_DARK : BAND_TEXT_LIGHT,
  };
}
