interface SwatchProps {
  color: string;
}

/** A small colour square for legends and chart keys. */
export function Swatch({ color }: SwatchProps) {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 shrink-0 rounded-sm"
      style={{ backgroundColor: color }}
    />
  );
}
