import { useAppStore } from '@/state/store';

interface DrawControlsProps {
  /** A 422 detail from the backend, or a client-side reason the shape was refused. */
  problem: string | null;
}

/** Draw / Clear buttons and the rejection message, overlaid on the map. */
export function DrawControls({ problem }: DrawControlsProps) {
  const mode = useAppStore((s) => s.mode);
  const area = useAppStore((s) => s.area);
  const setMode = useAppStore((s) => s.setMode);
  const clearArea = useAppStore((s) => s.clearArea);

  return (
    <div className="absolute top-3 right-3 flex flex-col items-end gap-2">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => {
            setMode(mode === 'draw' ? 'inspect' : 'draw');
          }}
          aria-pressed={mode === 'draw'}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm shadow aria-pressed:bg-slate-900 aria-pressed:text-white"
        >
          {mode === 'draw'
            ? 'Drawing… click to add points, click the first point to close'
            : 'Draw area'}
        </button>
        {area.kind === 'drawn' && (
          <button
            type="button"
            onClick={clearArea}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm shadow"
          >
            Clear drawing
          </button>
        )}
      </div>
      {problem !== null && (
        <p
          role="alert"
          className="max-w-sm rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 shadow"
        >
          {problem}
        </p>
      )}
    </div>
  );
}
