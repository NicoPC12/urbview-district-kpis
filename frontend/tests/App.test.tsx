import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
  window.history.replaceState(null, '', '/');
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
    expect(screen.getByTestId('kpi-value-crossing_density')).toHaveTextContent('22.6/km');
    expect(screen.queryByTestId('overlap-note')).not.toBeInTheDocument();

    // Drawing a polygon is, to the dashboard, a store change: every card must follow.
    act(() => {
      useAppStore.getState().setArea({ kind: 'drawn', geometry: SQUARE });
    });
    await waitFor(() => {
      expect(screen.getByTestId('kpi-value-low_speed_street_share')).toHaveTextContent('88.2 %');
    });
    expect(screen.getByTestId('kpi-value-crossing_density')).toHaveTextContent('9.1/km');
    expect(screen.getByTestId('kpi-value-green_space_distance_p50')).toHaveTextContent('210 m');
    expect(screen.getByTestId('overlap-note')).toHaveTextContent('57 % of your drawing has data');

    // Clearing the drawing returns to the district in one action.
    act(() => {
      useAppStore.getState().clearArea();
    });
    await waitFor(() => {
      expect(screen.getByTestId('kpi-value-low_speed_street_share')).toHaveTextContent('50.7 %');
    });
  });

  it('opens the area named in the URL, and drawing writes the URL back', async () => {
    window.history.replaceState(null, '', '/?area=2.16,41.39,2.17,41.39,2.17,41.397,2.16,41.397');
    render(<App />);

    // URL -> store -> query: the drawn-area numbers, not the district's.
    await waitFor(() => {
      expect(screen.getByTestId('kpi-value-low_speed_street_share')).toHaveTextContent('88.2 %');
    });
    expect(useAppStore.getState().area).toEqual({ kind: 'drawn', geometry: SQUARE });

    // Clearing the drawing takes the parameter back out.
    act(() => {
      useAppStore.getState().clearArea();
    });
    await waitFor(() => {
      expect(window.location.search).toBe('');
    });
    expect(await screen.findByTestId('kpi-value-low_speed_street_share')).toHaveTextContent(
      '50.7 %',
    );

    act(() => {
      useAppStore.getState().setArea({ kind: 'drawn', geometry: SQUARE });
    });
    await waitFor(() => {
      expect(window.location.search).toBe('?area=2.16,41.39,2.17,41.39,2.17,41.397,2.16,41.397');
    });
  });

  it('renders the empty state, not zeros, when sample_size is 0', async () => {
    server.use(http.post('/api/v1/kpis', () => Response.json(emptyResponse)));
    render(<App />);
    expect(await screen.findByTestId('kpi-value-low_speed_street_share')).toHaveTextContent(
      'no data',
    );
    expect(screen.getByTestId('kpi-value-low_speed_street_share')).not.toHaveTextContent('0');
    expect(screen.getByTestId('kpi-empty-low_speed_street_share')).toHaveTextContent(
      'No carriageway inside this area',
    );
    expect(screen.getByTestId('kpi-empty-green_space_distance_p50')).toHaveTextContent(
      'absence can mean unmapped',
    );
  });

  it('shows what n counts, the not-claim and the context figures on every card', async () => {
    render(<App />);
    const card = await screen.findByTestId('kpi-crossing_density');
    expect(card).toHaveTextContent('Based on 1,754 carriageway segments');
    expect(card).toHaveTextContent('Does not claim: A crossing point carries no quality.');
    expect(card).toHaveTextContent('(chosen, not cited)');
    expect(screen.getByTestId('kpi-low_speed_street_share')).toHaveTextContent(
      'carriageway with a mapped limit 89 %',
    );
  });

  it('dashboard -> map: a legend click sets the selected category, again clears it', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId('kpi-value-low_speed_street_share');
    const item = await screen.findByRole('button', { name: '30 km/h or less' });
    await user.click(item);
    expect(useAppStore.getState().selectedCategory).toBe('le30');
    expect(item).toHaveAttribute('aria-pressed', 'true');
    await user.click(item);
    expect(useAppStore.getState().selectedCategory).toBeNull();
  });

  it('map -> dashboard: a selected feature shows its contribution from the loaded layer', async () => {
    render(<App />);
    await screen.findByTestId('kpi-value-low_speed_street_share');
    act(() => {
      useAppStore.getState().selectFeature('seg-a');
    });
    const panel = await screen.findByTestId('feature-panel');
    expect(panel).toHaveTextContent("Carrer d'Aragó");
    expect(panel).toHaveTextContent('182 m of carriageway posted 30 km/h or less, 42 %');

    // Switching KPI drops the selection: the feature is not in the new layer.
    act(() => {
      useAppStore.getState().setActiveKpi('crossing_density');
    });
    await waitFor(() => {
      expect(screen.queryByTestId('feature-panel')).not.toBeInTheDocument();
    });
    expect(screen.getByTestId('breakdown-note')).toHaveTextContent('No breakdown');
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
