import type { Contribution } from './contribution';

interface FeaturePanelProps {
  contribution: Contribution | null;
  onClear: () => void;
}

/** Map → dashboard: what the clicked feature contributes to the active KPI. */
export function FeaturePanel({ contribution, onClear }: FeaturePanelProps) {
  if (contribution === null) {
    return (
      <p className="text-xs text-slate-500">
        Click a feature on the map to see what it contributes to this KPI.
      </p>
    );
  }
  return (
    <div
      data-testid="feature-panel"
      className="rounded border border-slate-900 bg-slate-50 px-3 py-2 text-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <strong>{contribution.title}</strong>
        <button type="button" onClick={onClear} className="text-xs text-slate-500 underline">
          clear
        </button>
      </div>
      <p className="mt-1 text-slate-700">{contribution.detail}</p>
    </div>
  );
}
