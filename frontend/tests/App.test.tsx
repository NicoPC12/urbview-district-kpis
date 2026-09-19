import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { App } from '@/App';

import { server } from './msw/server';

describe('App', () => {
  it('renders the app name and the backend health status', async () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1, name: 'UrbView' })).toBeInTheDocument();
    expect(await screen.findByTestId('api-status')).toHaveTextContent('ok');
    expect(screen.getByTestId('warehouse-status')).toHaveTextContent('loaded');
  });

  it('tells the user to build the warehouse when it is missing', async () => {
    server.use(
      http.get('/api/v1/health', () => HttpResponse.json({ status: 'ok', warehouse: false })),
    );
    render(<App />);
    expect(await screen.findByTestId('warehouse-status')).toHaveTextContent('make load-data');
  });

  it('shows an error when the backend is unreachable', async () => {
    server.use(http.get('/api/v1/health', () => HttpResponse.error()));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unreachable');
  });
});
