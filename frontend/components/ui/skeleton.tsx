import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-surface-raised", className)} />;
}

/** Loading state that echoes the MITRE-grid signature motif instead of a generic bar. */
export function GridSkeleton({ rows = 3, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div
      className="grid gap-1.5"
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
    >
      {Array.from({ length: rows * cols }).map((_, i) => (
        <div
          key={i}
          className="aspect-square animate-pulse rounded-sm bg-surface-raised"
          style={{ animationDelay: `${(i % cols) * 60}ms` }}
        />
      ))}
    </div>
  );
}
