import { cn } from "@/lib/utils";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("rounded-lg border border-line bg-surface", className)}>{children}</div>
  );
}

export function CardHeader({
  eyebrow,
  title,
  action,
}: {
  eyebrow?: string;
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between border-b border-line px-5 py-4">
      <div>
        {eyebrow && (
          <div className="font-mono text-[11px] uppercase tracking-wider text-mist">
            {eyebrow}
          </div>
        )}
        <h2 className="mt-0.5 font-display text-lg text-paper">{title}</h2>
      </div>
      {action}
    </div>
  );
}
