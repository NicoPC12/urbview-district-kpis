import type { HealthState } from '@/api/useHealth';

interface HealthLineProps {
  state: HealthState;
}

/** Presentational rendering of the backend health probe: loading, error or values. */
export function HealthLine({ state }: HealthLineProps) {
  switch (state.kind) {
    case 'loading':
      return <p role="status">Checking backend…</p>;
    case 'error':
      return (
        <p role="alert" className="text-red-700">
          Backend unreachable: {state.message}
        </p>
      );
    case 'ok':
      return (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
          <dt className="text-slate-500">API</dt>
          <dd data-testid="api-status">{state.health.status}</dd>
          <dt className="text-slate-500">Warehouse</dt>
          <dd data-testid="warehouse-status">
            {state.health.warehouse ? 'loaded' : 'not built — run make load-data'}
          </dd>
        </dl>
      );
  }
}
