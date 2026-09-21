import { act, render, screen, waitFor } from '@testing-library/react';
import { http } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from '@/App';
import { districtArea, useAppStore } from '@/state/store';

import { emptyResponse } from './fixtures/kpiResponse';
import { problem } from './msw/handlers';
import { server } from './msw/server';

// MapLibre needs WebGL, which jsdom does not have. The map's behaviour is covered by the pure
// modules it delegates to (layers.ts, selection.ts, geojson.ts); here it is a placeholder.
vi.mock('@/features/map/MapView', () => ({
  MapView: () => <div data-testid="map-placeholder" />,
}));

const SQUARE = {
  type: 'Polygon' as const,
  coordinates: [
    [
      [2.16, 41.39],
      [2.17, 41.39],
      [2.17, 41.397],
      [2.16, 41.397],
      [2.16, 41.39],
    ],
  ],
};

beforeEach(() => {
  useAppStore.setState({
    area: districtArea(),
    activeKpiKey: null,
    selectedCategory: null,
    selectedFeatureId: null,
    mode: 'inspect',
  });
});

describe('App', () => {
  it('shows the district KPIs, then the drawn area KPIs when the store area changes', async () => {
    render(<App />);
    expect(await screen.findByTestId('kpi-value-low_speed_street_share')).toHaveTextContent(
      '50.7 %',
    );
    expect(screen.getByTestId('kpi-value-crossing_density')).toHaveTextContent('22.6 /km');
    expect(screen.queryByTestId('overlap-note')).not.toBeInTheDocument();

    // Drawing a polygon is, to the dashboard, a store change: every card must follow.
    act(() => {
      useAppStore.getState().setArea({ kind: 'drawn', geometry: SQUARE });
    });
    await waitFor(() => {
      expect(screen.getByTestId('kpi-value-low_speed_street_share')).toHaveTextContent('88.2 %');
    });
    expect(screen.getByTestId('kpi-value-crossing_density')).toHaveTextContent('9.1 /km');
    expect(screen.getByTestId('kpi-value-green_space_distance_p50')).toHaveTextContent('210.0 m');
    expect(screen.getByTestId('overlap-note')).toHaveTextContent('57% of your drawing has data');

    // Clearing the drawing returns to the district in one action.
    act(() => {
      useAppStore.getState().clearArea();
    });
    await waitFor(() => {
      expect(screen.getByTestId('kpi-value-low_speed_street_share')).toHaveTextContent('50.7 %');
    });
  });

  it('renders the empty state, not zeros, when sample_size is 0', async () => {
    server.use(http.post('/api/v1/kpis', () => Response.json(emptyResponse)));
    render(<App />);
    expect(await screen.findByTestId('kpi-value-low_speed_street_share')).toHaveTextContent(
      'no data',
    );
    expect(screen.getByTestId('kpi-value-low_speed_street_share')).not.toHaveTextContent('0');
  });

  it('renders the load-data state on a 503', async () => {
    server.use(
      http.post('/api/v1/kpis', () =>
        problem(503, 'Warehouse not built', 'Run `make load-data`, then retry.'),
      ),
    );
    render(<App />);
    const state = await screen.findByTestId('warehouse-missing');
    expect(state).toHaveTextContent('Warehouse not loaded');
    expect(state).toHaveTextContent('make load-data');
  });
});
