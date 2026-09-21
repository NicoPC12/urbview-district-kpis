interface BandPillProps {
  label: string;
  background: string;
  color: string;
  /** "2 of 3", read by assistive tech so the ramp is not the only cue. */
  rankText: string;
}

/** A band label on the sequential ramp. Colours come in as props (lib/theme via bands.ts). */
export function BandPill({ label, background, color, rankText }: BandPillProps) {
  return (
    <span
      className="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ backgroundColor: background, color }}
      title={`Band ${rankText}`}
    >
      {label}
    </span>
  );
}
