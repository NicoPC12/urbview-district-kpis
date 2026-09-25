/**
 * The `?area=` integration, under StrictMode — the shape the browser actually runs.
 *
 * The pure codec is covered in `seams.test.ts`; these mount the real `App` with a URL in
 * `history` and assert what a reviewer sees: the drawn area's numbers, and an address bar
 * that still carries the parameter. A round-trip through the pure functions passed happily
 * while the feature was broken, so these go through the component tree instead.
 */

import { act, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from '@/App';
import { districtArea, useAppStore } from '@/state/store';

// MapLibre needs WebGL, which jsdom has not; the map's own seams are tested separately.
vi.mock('@/features/map/MapView', () => ({
  MapView: () => <div data-testid="map-placeholder" />,
}));

/** The Sant Antoni superblock link from NOTES.md and the README, verbatim. */
const A_SEARCH = '?area=2.15326,41.38205,2.15668,41.38457,2.16331,41.37945,2.15989,41.37693';

function renderApp() {
  return render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

beforeEach(() => {
  useAppStore.setState({
    area: districtArea(),
    activeKpiKey: null,
    selectedCategory: null,
    selectedFeatureId: null,
    mode: 'inspect',
  });
});

describe('?area= in the address bar', () => {
  it('the store reads the URL when it is created, so the first render is already the area', async () => {
    window.history.replaceState(null, '', A_SEARCH);
    vi.resetModules(); // re-evaluate the store module the way a page load does
    const { useAppStore: freshStore } = await import('@/state/store');
    expect(freshStore.getState().area.kind).toBe('drawn');
  });

  it('opens a reference-area link on that area, and keeps the parameter', async () => {
    window.history.replaceState(null, '', A_SEARCH);
    renderApp();

    // The drawn-area numbers, not the district's.
    await waitFor(() => {
      expect(screen.getByTestId('kpi-value-low_speed_street_share')).toHaveTextContent('88.2 %');
    });
    expect(screen.getByTestId('overlap-note')).toBeInTheDocument();
    expect(useAppStore.getState().area.kind).toBe('drawn');

    // And the link is still shareable after mount: this is the assertion that failed while
    // the bug was live, because the writer pushed the default district over the parameter.
    expect(window.location.search).toBe(A_SEARCH);
  });

  it('opens the district when the parameter is malformed, and drops it from the URL', async () => {
    window.history.replaceState(null, '', '?area=not-a-polygon');
    renderApp();

    expect(await screen.findByTestId('kpi-value-low_speed_street_share')).toHaveTextContent(
      '50.7 %',
    );
    expect(useAppStore.getState().area).toEqual(districtArea());
    await waitFor(() => {
      expect(window.location.search).toBe('');
    });
  });

  it('opens the district when there is no parameter, and leaves the URL clean', async () => {
    window.history.replaceState(null, '', '/');
    renderApp();

    expect(await screen.findByTestId('kpi-value-low_speed_street_share')).toHaveTextContent(
      '50.7 %',
    );
    expect(window.location.search).toBe('');
  });

  it('writes the URL when the area changes, and reads it back on Back', async () => {
    window.history.replaceState(null, '', '/');
    renderApp();
    await screen.findByTestId('kpi-value-low_speed_street_share');

    const drawn = {
      kind: 'drawn' as const,
      geometry: {
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
      },
    };
    act(() => {
      useAppStore.getState().setArea(drawn);
    });
    await waitFor(() => {
      expect(window.location.search).toBe('?area=2.16,41.39,2.17,41.39,2.17,41.397,2.16,41.397');
    });

    // Back: history returns to "/" and the store follows it to the district.
    act(() => {
      window.history.back();
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    await waitFor(() => {
      expect(useAppStore.getState().area).toEqual(districtArea());
    });
  });
});
