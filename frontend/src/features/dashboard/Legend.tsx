import type { LegendItem } from '@/api/schema.gen';
import { Swatch } from '@/components/ui/Swatch';

interface LegendProps {
  items: LegendItem[];
  selectedCategory: string | null;
  onToggleCategory: (category: string) => void;
}

/** The active KPI's map categories from the API; clicking one filters the map. */
export function Legend({ items, selectedCategory, onToggleCategory }: LegendProps) {
  if (items.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Map legend">
      {items.map((item) => {
        const selected = selectedCategory === item.key;
        const dimmed = selectedCategory !== null && !selected;
        return (
          <li key={item.key}>
            <button
              type="button"
              aria-pressed={selected}
              onClick={() => {
                onToggleCategory(item.key);
              }}
              className={`flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs ${
                selected ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white'
              } ${dimmed ? 'opacity-50' : ''}`}
            >
              <Swatch color={item.color} />
              {item.label}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
