/**
 * The dashboard half of the page. Talks to the map only through the store.
 *
 * Reads the same query the map reads (TanStack dedupes by area), so the numbers and the
 * features on screen always come from one response.
 */

import { useEffect } from 'react';

import { ApiError } from '@/api/client';
import { useKpis } from '@/api/useKpis';
import { useAppStore } from '@/state/store';

/** Area header, KPI cards, chart, legend, insights and the selected feature's contribution. */
export function Dashboard() {
  const area = useAppStore((s) => s.area);
  const activeKpiKey = useAppStore((s) => s.activeKpiKey);
  const setActiveKpi = useAppStore((s) => s.setActiveKpi);
  const clearArea = useAppStore((s) => s.clearArea);
  const query = useKpis(area);
  const data = query.data;

  // The first response decides which KPI's layer and chart are shown until the user picks.
  useEffect(() => {
    const first = data?.kpis[0];
    if (activeKpiKey === null && first !== undefined) setActiveKpi(first.key);
  }, [data, activeKpiKey, setActiveKpi]);

  if (data === undefined) {
    if (query.isPending) {
      return (
        <p role="status" data-testid="dashboard-loading">
          Loading KPIs…
        </p>
      );
    }
    if (query.error instanceof ApiError && query.error.status === 503) {
      return (
        <section role="alert" data-testid="warehouse-missing">
          <h2>Warehouse not loaded</h2>
          <p>{query.error.problem.detail}</p>
          <p>
            Run <code>make load-data</code>, then{' '}
            <button
              type="button"
              onClick={() => {
                void query.refetch();
              }}
            >
              retry
            </button>
            .
          </p>
        </section>
      );
    }
    return (
      <section role="alert">
        <p>Could not load KPIs: {query.error.message}</p>
        <button
          type="button"
          onClick={() => {
            void query.refetch();
          }}
        >
          Retry
        </button>
      </section>
    );
  }

  return (
    <div data-testid="dashboard" aria-busy={query.isPlaceholderData || query.isFetching}>
      <header>
        <h2>
          {data.area.name} — {data.area.km2.toFixed(2)} km² ({data.area.source})
        </h2>
        {data.area.district_overlap_share < 1 && (
          <p data-testid="overlap-note">
            {Math.round(data.area.district_overlap_share * 100)}% of your drawing has data
          </p>
        )}
        {(query.isPlaceholderData || query.isFetching) && <p role="status">Recomputing…</p>}
        {area.kind === 'drawn' && (
          <button type="button" onClick={clearArea}>
            Clear drawing
          </button>
        )}
      </header>
      <ul>
        {data.kpis.map((kpi) => (
          <li key={kpi.key} data-testid={`kpi-${kpi.key}`}>
            <button
              type="button"
              onClick={() => {
                setActiveKpi(kpi.key);
              }}
              aria-pressed={kpi.key === activeKpiKey}
            >
              {kpi.label}
            </button>
            :{' '}
            <span data-testid={`kpi-value-${kpi.key}`}>
              {kpi.value === null ? 'no data' : `${kpi.value.toFixed(1)} ${kpi.unit}`}
            </span>{' '}
            {kpi.band !== null && <span>({kpi.band})</span>} · n={kpi.sample_size}
          </li>
        ))}
      </ul>
      <ul>
        {data.insights.map((insight) => (
          <li key={insight}>{insight}</li>
        ))}
      </ul>
    </div>
  );
}
