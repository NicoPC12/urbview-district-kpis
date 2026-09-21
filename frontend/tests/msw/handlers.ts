import { http, HttpResponse } from 'msw';

import type { KpiRequestRequest } from '@/api/schema.gen';

import { district, districtResponse, drawnResponse } from '../fixtures/kpiResponse';

/** Default mocked API: a built warehouse; the district and any drawn polygon answer. */
export const handlers = [
  http.get('/api/v1/health', () => HttpResponse.json({ status: 'ok', warehouse: true })),
  http.get('/api/v1/districts', () => HttpResponse.json([district])),
  http.post('/api/v1/kpis', async ({ request }) => {
    const body = (await request.json()) as KpiRequestRequest;
    return HttpResponse.json(body.district !== undefined ? districtResponse : drawnResponse);
  }),
];

/** An RFC 7807 body the way the backend sends it. */
export function problem(status: number, title: string, detail: string) {
  return HttpResponse.json(
    { type: 'about:blank', title, status, detail },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  );
}
