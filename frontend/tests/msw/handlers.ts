import { http, HttpResponse } from 'msw';

/** Default mocked API: a healthy backend with a built warehouse. */
export const handlers = [
  http.get('/api/v1/health', () => HttpResponse.json({ status: 'ok', warehouse: true })),
];
