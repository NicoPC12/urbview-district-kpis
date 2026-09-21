/**
 * Server state: KPI responses keyed by the area selection, and the district catalogue.
 *
 * The area is the query key, so drawing a polygon *is* the refetch. `keepPreviousData`
 * keeps the last numbers on screen (with `isPlaceholderData` true) while the new ones load,
 * and TanStack's `signal` is passed into fetch so a second drawing aborts the first request.
 */

import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query';

import { ApiError, fetchDistricts, fetchKpis } from '@/api/client';
import type { District, KpiResponse } from '@/api/schema.gen';
import { areaToRequest } from '@/features/area/selection';
import type { AreaSelection } from '@/state/store';

/** Query key for an area; exported so tests and the context layer share it. */
export function kpiQueryKey(area: AreaSelection): readonly ['kpis', AreaSelection] {
  return ['kpis', area];
}

/** A 4xx/5xx the backend described is final; only network failures are worth a retry. */
function retryUnlessProblem(failureCount: number, error: Error): boolean {
  return !(error instanceof ApiError) && failureCount < 2;
}

/** Every KPI, layer, insight and legend item for an area. */
export function useKpis(area: AreaSelection): UseQueryResult<KpiResponse> {
  return useQuery({
    queryKey: kpiQueryKey(area),
    queryFn: ({ signal }) => fetchKpis(areaToRequest(area), signal),
    placeholderData: keepPreviousData,
    staleTime: Infinity, // the backend's own cache decides freshness
    retry: retryUnlessProblem,
  });
}

/** Districts with their outlines: what the map draws and fits to on load. */
export function useDistricts(): UseQueryResult<District[]> {
  return useQuery({
    queryKey: ['districts'],
    queryFn: ({ signal }) => fetchDistricts(signal),
    staleTime: Infinity,
    retry: retryUnlessProblem,
  });
}
