/**
 * Two-way sync between the store's area and the URL.
 *
 * On mount the URL wins (a shared link must open what it points at); afterwards a store
 * change rewrites the URL, and Back/Forward put the store back. `replaceState` on the first
 * write and `pushState` after, so drawing adds one history entry per area, not per render.
 */

import { useEffect, useRef } from 'react';

import { useAppStore } from '@/state/store';

import { areaFromSearch, searchForArea } from './url';

/** Wire `?area=` to the store. Call once, at the top of the app. */
export function useAreaUrl(): void {
  const area = useAppStore((s) => s.area);
  const setArea = useAppStore((s) => s.setArea);
  const applied = useRef(false);

  // URL -> store, once on mount and on every Back/Forward.
  useEffect(() => {
    const fromUrl = (): void => {
      setArea(areaFromSearch(window.location.search));
      applied.current = true;
    };
    fromUrl();
    window.addEventListener('popstate', fromUrl);
    return () => {
      window.removeEventListener('popstate', fromUrl);
    };
  }, [setArea]);

  // store -> URL, skipping the write that would only repeat what the URL already says.
  useEffect(() => {
    if (!applied.current) return;
    const next = `${window.location.pathname}${searchForArea(area)}`;
    const current = `${window.location.pathname}${window.location.search}`;
    if (next === current) return;
    window.history.pushState(null, '', next);
  }, [area]);
}
