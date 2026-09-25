/**
 * Keep the address bar and the store's area in step, in both directions.
 *
 * The bug this shape exists to prevent: effects of one commit all see the area from the
 * render that queued them. A reader effect that called `setArea` therefore left a sibling
 * writer effect holding the *previous* area — the default district — and the writer pushed
 * that over the incoming `?area=`. Under StrictMode the immediate re-run then read the wiped
 * URL back into the store, so a shared link opened on the district.
 *
 * So the writer is a store subscription, not an effect: a subscriber is called with the
 * state that was actually committed and can never hold a stale area. The subscription is
 * attached before the first read, so the read itself finds the URL already matching and
 * writes nothing. `state/store` additionally seeds the area from the URL at creation, which
 * saves a fresh page load one request for the district it is about to replace.
 *
 * Pinned by `tests/areaUrl.test.tsx`, which mounts the real app under StrictMode.
 */

import { useEffect } from 'react';

import { areaFromSearch, urlForArea } from '@/lib/areaUrl';
import { districtArea, useAppStore } from '@/state/store';

/** Wire `?area=` to the store. Call once, at the top of the app. */
export function useAreaUrl(): void {
  useEffect(() => {
    const currentUrl = (): string => `${window.location.pathname}${window.location.search}`;

    // store -> URL. Subscribed first, so the read below is already reconciled when it lands.
    const unsubscribe = useAppStore.subscribe((state, previous) => {
      if (state.area === previous.area) return;
      const next = urlForArea(state.area);
      if (next !== currentUrl()) window.history.pushState(null, '', next);
    });

    // URL -> store, on mount and on Back/Forward.
    const fromUrl = (): void => {
      const area = areaFromSearch(window.location.search) ?? districtArea();
      useAppStore.getState().setArea(area);
      // A malformed or absent parameter resolves to the district: say so in the address bar.
      const next = urlForArea(area);
      if (next !== currentUrl()) window.history.replaceState(null, '', next);
    };
    fromUrl();
    window.addEventListener('popstate', fromUrl);

    return () => {
      window.removeEventListener('popstate', fromUrl);
      unsubscribe();
    };
  }, []);
}
