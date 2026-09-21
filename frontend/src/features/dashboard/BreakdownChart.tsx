import {
  Bar,
  BarChart,
  Rectangle,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type BarShapeProps,
} from 'recharts';

import type { Kpi, LegendItem } from '@/api/schema.gen';
import { FALLBACK_COLOR } from '@/lib/theme';

interface BreakdownChartProps {
  kpi: Kpi;
  legend: LegendItem[];
  selectedCategory: string | null;
  /** Dashboard → map: a bar click emphasises that category on the map. */
  onToggleCategory: (category: string) => void;
}

const DIM = 0.3;

/** One bar per breakdown slice, coloured like the map; clicking a bar filters the map. */
export function BreakdownChart({
  kpi,
  legend,
  selectedCategory,
  onToggleCategory,
}: BreakdownChartProps) {
  if (kpi.breakdown === undefined || kpi.breakdown.length === 0) {
    return (
      <p className="text-sm text-slate-500" data-testid="breakdown-note">
        {kpi.breakdown_note ?? 'No breakdown for this KPI.'}
      </p>
    );
  }
  const colorOf = (key: string): string =>
    legend.find((i) => i.key === key)?.color ?? FALLBACK_COLOR;
  const data = kpi.breakdown;

  // Per-bar colour and dimming through the `shape` prop (Recharts 3 retired <Cell>).
  const shape = (props: BarShapeProps) => {
    const slice = data[props.index];
    const key = slice?.key ?? '';
    return (
      <Rectangle
        x={props.x}
        y={props.y}
        width={props.width}
        height={props.height}
        fill={colorOf(key)}
        fillOpacity={selectedCategory === null || selectedCategory === key ? 1 : DIM}
        className="cursor-pointer"
      />
    );
  };

  return (
    <div className="h-44" data-testid="breakdown-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 12 }} />
          <Tooltip
            cursor={{ fill: 'transparent' }}
            formatter={(value) => [`${String(value)} ${kpi.unit === '%' ? 'km' : kpi.unit}`, '']}
          />
          <Bar
            dataKey="value"
            isAnimationActive={false}
            shape={shape}
            onClick={(_item, index) => {
              const slice = data[index];
              if (slice !== undefined) onToggleCategory(slice.key);
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
