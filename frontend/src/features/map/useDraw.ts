/**
 * terra-draw on the map: polygon mode, one polygon at a time, finish → `setArea`.
 *
 * The hook owns nothing but wiring. The geometry check lives in `finishDrawing` (pure);
 * the mode lives in the store, so the dashboard's "Clear drawing" and the map's button are
 * the same action. While `mode === 'draw'`, MapView suppresses feature clicks so the draw
 * tool alone consumes them.
 */

import type { Map as MapLibreMap } from 'maplibre-gl';
import { useEffect, useRef, useState } from 'react';
import { TerraDraw, TerraDrawPolygonMode } from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';

import { finishDrawing } from '@/features/area/selection';
import { useAppStore } from '@/state/store';

export interface UseDrawResult {
  /** Why the last finished shape was not accepted client-side, if so. */
  drawProblem: string | null;
}

/** Wire terra-draw to the map and the store. */
export function useDraw(map: MapLibreMap | null): UseDrawResult {
  const drawRef = useRef<TerraDraw | null>(null);
  const [drawProblem, setDrawProblem] = useState<string | null>(null);
  const mode = useAppStore((s) => s.mode);
  const area = useAppStore((s) => s.area);
  const setArea = useAppStore((s) => s.setArea);
  const setMode = useAppStore((s) => s.setMode);

  useEffect(() => {
    if (map === null) return;
    const draw = new TerraDraw({
      adapter: new TerraDrawMapLibreGLAdapter({ map }),
      modes: [new TerraDrawPolygonMode()],
    });
    draw.start();
    draw.setMode('static');
    draw.on('finish', (id, context) => {
      if (context.action !== 'draw') return;
      const feature = draw.getSnapshotFeature(id);
      const result = finishDrawing(feature?.geometry);
      if (result.ok) {
        setDrawProblem(null);
        setArea(result.area);
      } else {
        setDrawProblem(result.reason);
        draw.clear();
        setMode('inspect');
      }
    });
    drawRef.current = draw;
    return () => {
      drawRef.current = null;
      draw.stop();
    };
  }, [map, setArea, setMode]);

  // Entering draw mode starts a fresh polygon: the previous drawing goes.
  useEffect(() => {
    const draw = drawRef.current;
    if (draw === null) return;
    if (mode === 'draw') {
      draw.clear();
      draw.setMode('polygon');
    } else {
      draw.setMode('static');
    }
  }, [mode, map]);

  // Keep the drawn shape in step with the store: cleared for the district, and restored when
  // the area came from the URL (a shared link must show the polygon it computed, not a bare map).
  useEffect(() => {
    const draw = drawRef.current;
    if (draw === null || map === null) return;
    draw.clear();
    if (area.kind === 'drawn') {
      draw.addFeatures([
        { type: 'Feature', geometry: area.geometry, properties: { mode: 'polygon' } },
      ]);
    }
  }, [area, map]);

  return { drawProblem };
}
