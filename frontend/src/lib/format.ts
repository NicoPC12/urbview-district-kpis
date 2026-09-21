/** Number formatting shared by cards, chart, insights and the feature panel. */

const integer = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const oneDecimal = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });

/** `1,883` */
export function formatInt(value: number): string {
  return integer.format(value);
}

/** A KPI value with its unit: `50.7 %`, `362 m`, `22.6 /km`. */
export function formatValue(value: number, unit: string): string {
  const digits = unit === 'm' || Math.abs(value) >= 1000 ? integer : oneDecimal;
  const sep = unit.startsWith('/') || unit === '' ? '' : ' ';
  return `${digits.format(value)}${sep}${unit}`;
}

/** `42 %` from a 0–1 share. */
export function formatShare(share: number): string {
  return `${integer.format(share * 100)} %`;
}

/** Metres with a sensible unit: `182 m`, `1.4 km`. */
export function formatMetres(metres: number): string {
  return metres >= 1000 ? `${oneDecimal.format(metres / 1000)} km` : `${integer.format(metres)} m`;
}
