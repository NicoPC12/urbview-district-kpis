import { useEffect, useState } from 'react';

import { fetchHealth } from './client';
import type { Health } from './schema.gen';

/** Discriminated request state for the health probe. */
export type HealthState =
  { kind: 'loading' } | { kind: 'ok'; health: Health } | { kind: 'error'; message: string };

/**
 * Load the backend health probe once on mount.
 *
 * Plain `useEffect` + `fetch` on purpose: TanStack Query lands in Phase 5 with the KPI
 * queries, and one probe does not justify pulling it in earlier.
 */
export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({ kind: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((health) => {
        setState({ kind: 'ok', health });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : 'Unknown error';
        setState({ kind: 'error', message });
      });
    return () => {
      controller.abort();
    };
  }, []);

  return state;
}
