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

/** Reference area A — the polygon the fixture's drawn response was captured for. */
const AREA_A = {
  type: 'Polygon' as const,
  coordinates: [
    [
      [2.15326, 41.38205],
      [2.15668, 41.38457],
      [2.16331, 41.37945],
      [2.15989, 41.37693],
      [2.15326, 41.38205],
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

    // Drawing a polygon is, to the dashboard, a store change: every card must follow.
    act(() => {
      useAppStore.getState().setArea({ kind: 'drawn', geometry: AREA_A });
    });
    await waitFor(() => {
      expect(screen.getByTestId('kpi-value-low_speed_street_share')).toHaveTextContent('63.6 %');
    });
    expect(screen.getByTestId('kpi-value-crossing_density')).toHaveTextContent('20.9/km');
    expect(screen.getByTestId('kpi-value-green_space_distance_p50')).toHaveTextContent('595 m');
    expect(screen.getByTestId('kpi-value-pedestrian_network_share')).toHaveTextContent('26 %');

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
    expect(screen.getByTestId('kpi-empty-low_speed_street_share')).toHaveTextContent(
      'No carriageway inside this area',
    );
    expect(screen.getByTestId('kpi-empty-green_space_distance_p50')).toHaveTextContent(
      'absence can mean unmapped',
    );
    // Nothing of the drawing lies in the district, so the dashboard says how much has data.
    expect(screen.getByTestId('overlap-note')).toHaveTextContent('0 % of your drawing has data');
  });

  it('shows what n counts, the not-claim and the context figures on every card', async () => {
    render(<App />);
    const card = await screen.findByTestId('kpi-crossing_density');
    expect(card).toHaveTextContent('Based on 1,754 carriageway segments');
    expect(card).toHaveTextContent('Does not claim: A crossing point carries no quality');
    expect(card).toHaveTextContent('fewer marked crossings can mean the whole street has become');
    // Four KPIs band against Eixample's own distribution; that must be visible on the card.
    expect(screen.getByTestId('kpi-relative-crossing_density')).toHaveTextContent(
      'thirds of Eixample’s 250 m cells',
    );
    expect(screen.getByTestId('kpi-low_speed_street_share')).toHaveTextContent(
      'carriageway with a mapped limit 89 %',
    );
  });

  it('dashboard -> map: a legend click sets the selected category, again clears it', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId('kpi-value-low_speed_street_share');
    const item = await screen.findByRole('button', { name: '≤ 20 km/h' });
    await user.click(item);
    expect(useAppStore.getState().selectedCategory).toBe('le20');
    expect(item).toHaveAttribute('aria-pressed', 'true');
    await user.click(item);
    expect(useAppStore.getState().selectedCategory).toBeNull();
  });

  it('map -> dashboard: a selected feature shows its contribution from the loaded layer', async () => {
    render(<App />);
    await screen.findByTestId('kpi-value-low_speed_street_share');
    act(() => {
      // The first street in the district fixture's speed layer.
      useAppStore.getState().selectFeature('9ea11987-45a3-4f6b-ba9c-ec55d962398a');
    });
    const panel = await screen.findByTestId('feature-panel');
    expect(panel).toHaveTextContent('Plaça de Francesc Macià');
    expect(panel).toHaveTextContent('20 m of carriageway posted 31–50 km/h');

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
