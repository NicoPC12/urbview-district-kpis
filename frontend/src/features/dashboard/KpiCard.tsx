import type { Kpi } from '@/api/schema.gen';
import { BandPill } from '@/components/ui/BandPill';
import { formatInt, formatValue } from '@/lib/format';

import { bandStyle } from './bands';

interface KpiCardProps {
  kpi: Kpi;
  active: boolean;
  onActivate: () => void;
}

/** What `sample_size` counts, by denominator, so "n = 1,883" cannot read as "1,883 crossings". */
const SAMPLE_NOUN: Record<Kpi['denominator'], string> = {
  carriageway_length_m: 'carriageway segments',
  network_length_m: 'street segments',
  building_count: 'buildings',
};

/** What is missing when a KPI is empty, by denominator. */
const EMPTY_NOUN: Record<Kpi['denominator'], string> = {
  carriageway_length_m: 'carriageway',
  network_length_m: 'mapped streets',
  building_count: 'buildings',
};

/** One KPI: value, band, definition, what it does not claim, context — all on the card. */
export function KpiCard({ kpi, active, onActivate }: KpiCardProps) {
  const band = bandStyle(kpi);
  const empty = kpi.sample_size === 0;

  return (
    <article
      data-testid={`kpi-${kpi.key}`}
      aria-current={active ? 'true' : undefined}
      className={`rounded-lg border bg-white p-4 transition-colors ${
        active ? 'border-sky-600 ring-1 ring-sky-600' : 'border-slate-200 hover:border-slate-400'
      }`}
    >
      <button type="button" onClick={onActivate} className="w-full text-left" aria-pressed={active}>
        <h3 className="text-sm font-medium text-slate-700">{kpi.label}</h3>
        <div className="mt-1 flex items-baseline gap-3">
          <span
            data-testid={`kpi-value-${kpi.key}`}
            className={`text-3xl font-semibold tracking-tight ${empty ? 'text-slate-400' : ''}`}
          >
            {kpi.value === null ? 'no data' : formatValue(kpi.value, kpi.unit)}
          </span>
          {band !== null && kpi.band !== null && (
            <BandPill
              label={kpi.band}
              background={band.background}
              color={band.color}
              rankText={`${String(band.rank + 1)} of ${String(band.total)}`}
            />
          )}
        </div>
      </button>

      {empty ? (
        <p className="mt-2 text-sm text-slate-600" data-testid={`kpi-empty-${kpi.key}`}>
          No {EMPTY_NOUN[kpi.denominator]} inside this area. In Overture, absence can mean unmapped
          rather than not there.
        </p>
      ) : (
        <p className="mt-2 text-xs text-slate-500">
          Based on {formatInt(kpi.sample_size)} {SAMPLE_NOUN[kpi.denominator]}
          {kpi.context
            .filter((c) => c.value !== null)
            .map((c) => ` · ${c.label.toLowerCase()} ${formatValue(c.value ?? 0, c.unit)}`)
            .join('')}
        </p>
      )}

      <p className="mt-2 text-sm text-slate-700">{kpi.definition}</p>
      <p className="mt-1 text-sm text-slate-500">
        <span className="font-medium text-slate-600">Does not claim: </span>
        {kpi.not_claim}
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Bands:{' '}
        {kpi.bands
          .map((b) => `${b.label}${b.max === null ? '' : ` ≤ ${String(b.max)}`}`)
          .join(' · ')}
        {' — '}
        {kpi.source.url === null ? (
          <span>{kpi.source.label}</span>
        ) : (
          <a href={kpi.source.url} target="_blank" rel="noreferrer" className="underline">
            {kpi.source.label}
          </a>
        )}
        {kpi.source.kind === 'chosen' && ' (chosen, not cited)'}
      </p>
      {/* Four KPIs band against Eixample's own distribution and one against a WHO distance;
          on one screen those must not read as the same kind of number. */}
      {kpi.source.kind === 'derived' && (
        <p
          data-testid={`kpi-relative-${kpi.key}`}
          className="mt-1 inline-block rounded bg-sky-50 px-1.5 py-0.5 text-xs text-sky-900"
        >
          Relative bands — thirds of Eixample&rsquo;s 250 m cells, not an absolute standard
        </p>
      )}
    </article>
  );
}
