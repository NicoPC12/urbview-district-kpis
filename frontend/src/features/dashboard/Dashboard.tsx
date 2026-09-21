/**
 * The dashboard half of the page. Talks to the map only through the store.
 *
 * Reads the same query the map reads (TanStack dedupes by area), so the numbers and the
 * features on screen always come from one response. States: first-load skeletons,
 * "recomputing" while a new area loads over the previous numbers, warehouse-not-built (503),
 * generic error with retry, and per-card empty when `sample_size` is 0.
 */

import { useEffect } from 'react';

import { ApiError } from '@/api/client';
import { useKpis } from '@/api/useKpis';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatShare } from '@/lib/format';
import { useAppStore } from '@/state/store';

import { BreakdownChart } from './BreakdownChart';
import { describeContribution } from './contribution';
import { FeaturePanel } from './FeaturePanel';
import { KpiCard } from './KpiCard';
import { Legend } from './Legend';

/** Area header, KPI cards, chart, legend, insights and the selected feature's contribution. */
export function Dashboard() {
  const area = useAppStore((s) => s.area);
  const activeKpiKey = useAppStore((s) => s.activeKpiKey);
  const selectedCategory = useAppStore((s) => s.selectedCategory);
  const selectedFeatureId = useAppStore((s) => s.selectedFeatureId);
  const setActiveKpi = useAppStore((s) => s.setActiveKpi);
  const toggleCategory = useAppStore((s) => s.toggleCategory);
  const selectFeature = useAppStore((s) => s.selectFeature);
  const clearArea = useAppStore((s) => s.clearArea);
  const query = useKpis(area);
  const data = query.data;

  // The first response decides which KPI's layer and chart are shown until the user picks.
  useEffect(() => {
    const first = data?.kpis[0];
    if (activeKpiKey === null && first !== undefined) setActiveKpi(first.key);
  }, [data, activeKpiKey, setActiveKpi]);

  if (data === undefined) {
    if (query.isPending) return <DashboardSkeleton />;
    if (query.error instanceof ApiError && query.error.status === 503) {
      return (
        <section role="alert" data-testid="warehouse-missing" className="mt-6 space-y-2">
          <h2 className="text-lg font-semibold">Warehouse not loaded</h2>
          <p className="text-sm text-slate-700">{query.error.problem.detail}</p>
          <p className="text-sm">
            Run <code className="rounded bg-slate-100 px-1">make load-data</code>, then{' '}
            <RetryButton onClick={() => void query.refetch()} label="retry" />.
          </p>
        </section>
      );
    }
    return (
      <section role="alert" className="mt-6 space-y-2">
        <h2 className="text-lg font-semibold">Could not load the KPIs</h2>
        <p className="text-sm text-slate-700">{query.error.message}</p>
        <RetryButton onClick={() => void query.refetch()} label="Retry" />
      </section>
    );
  }

  const recomputing = query.isPlaceholderData || query.isFetching;
  const activeKpi = data.kpis.find((k) => k.key === activeKpiKey) ?? data.kpis[0];
  const legend = data.legend.items.filter((i) => i.kpi_key === activeKpi?.key);
  const contribution =
    activeKpi !== undefined && selectedFeatureId !== null
      ? describeContribution(data, activeKpi.key, selectedFeatureId)
      : null;

  return (
    <div data-testid="dashboard" aria-busy={recomputing} className="space-y-5">
      <header className="mt-3">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-lg font-semibold">
            {data.area.name}{' '}
            <span className="font-normal text-slate-500">
              · {data.area.km2.toFixed(2)} km² ·{' '}
              {data.area.source === 'district' ? 'whole district' : 'drawn'}
            </span>
          </h2>
          {area.kind === 'drawn' && (
            <button
              type="button"
              onClick={clearArea}
              className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50"
            >
              Clear drawing
            </button>
          )}
        </div>
        {data.area.district_overlap_share < 1 && (
          <p data-testid="overlap-note" className="mt-1 text-sm text-amber-800">
            {formatShare(data.area.district_overlap_share)} of your drawing has data — the numbers
            describe the part inside{' '}
            {data.area.district_overlap_share === 0
              ? 'the district, and nothing is'
              : 'the district'}
            .
          </p>
        )}
        <p
          role="status"
          className={`mt-1 text-xs text-slate-500 ${recomputing ? '' : 'invisible'}`}
        >
          Recomputing for the new area…
        </p>
      </header>

      <section aria-label="KPIs" className={`grid gap-3 ${recomputing ? 'opacity-60' : ''}`}>
        {data.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            kpi={kpi}
            active={kpi.key === activeKpi?.key}
            onActivate={() => {
              setActiveKpi(kpi.key);
            }}
          />
        ))}
      </section>

      {activeKpi !== undefined && (
        <section
          aria-label="Active KPI"
          className="space-y-3 rounded-lg border border-slate-200 p-4"
        >
          <h3 className="text-sm font-medium text-slate-700">On the map: {activeKpi.label}</h3>
          <BreakdownChart
            kpi={activeKpi}
            legend={legend}
            selectedCategory={selectedCategory}
            onToggleCategory={toggleCategory}
          />
          <Legend
            items={legend}
            selectedCategory={selectedCategory}
            onToggleCategory={toggleCategory}
          />
          <FeaturePanel
            contribution={contribution}
            onClear={() => {
              selectFeature(null);
            }}
          />
        </section>
      )}

      <section aria-label="Insights">
        <h3 className="text-sm font-medium text-slate-700">What the numbers say</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {data.insights.map((insight) => (
            <li key={insight}>{insight}</li>
          ))}
        </ul>
      </section>

      <footer className="text-xs text-slate-400">
        Overture Maps {data.meta.overture_release} · computed in {Math.round(data.meta.computed_ms)}{' '}
        ms
        {data.meta.cached ? ' (cached)' : ''} · every number from Overture; the basemap is context
        only
      </footer>
    </div>
  );
}

interface RetryButtonProps {
  onClick: () => void;
  label: string;
}

function RetryButton({ onClick, label }: RetryButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded border border-slate-300 px-2 py-1 text-sm hover:bg-slate-50"
    >
      {label}
    </button>
  );
}

function DashboardSkeleton() {
  return (
    <div
      data-testid="dashboard-loading"
      role="status"
      aria-label="Loading KPIs"
      className="mt-3 space-y-4"
    >
      <Skeleton className="h-6 w-2/3" />
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="space-y-2 rounded-lg border border-slate-200 p-4">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </div>
      ))}
    </div>
  );
}
