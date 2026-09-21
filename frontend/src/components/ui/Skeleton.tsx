interface SkeletonProps {
  /** Tailwind classes for size; the block pulses in a neutral grey. */
  className?: string;
}

/** A pulsing placeholder block for the first load. */
export function Skeleton({ className = 'h-4 w-full' }: SkeletonProps) {
  return <div aria-hidden="true" className={`animate-pulse rounded bg-slate-200 ${className}`} />;
}
