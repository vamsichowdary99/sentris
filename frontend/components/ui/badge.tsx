import { cn } from "@/lib/utils";
import type { AlertStatus, CaseStatus, Severity } from "@/lib/types";

function Badge({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider",
        className,
      )}
    >
      {children}
    </span>
  );
}

const severityStyles: Record<Severity, string> = {
  info: "border-line text-mist bg-surface-raised",
  low: "border-cyan-dim/60 text-cyan bg-cyan-dim/10",
  medium: "border-amber-dim/60 text-amber/80 bg-amber-dim/10",
  high: "border-amber/50 text-amber bg-amber-dim/20",
  critical: "border-threat/60 text-threat bg-threat-dim/20",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge className={severityStyles[severity]}>
      {severity === "critical" && (
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-threat" />
      )}
      {severity}
    </Badge>
  );
}

const alertStatusStyles: Record<AlertStatus, string> = {
  new: "border-cyan-dim/60 text-cyan bg-cyan-dim/10",
  triaging: "border-amber-dim/60 text-amber/80 bg-amber-dim/10",
  investigating: "border-amber/50 text-amber bg-amber-dim/20",
  closed: "border-line text-mist bg-surface-raised",
  false_positive: "border-line text-mist/60 bg-surface-raised line-through",
};

const alertStatusLabels: Record<AlertStatus, string> = {
  new: "new",
  triaging: "triaging",
  investigating: "investigating",
  closed: "closed",
  false_positive: "false positive",
};

export function AlertStatusBadge({ status }: { status: AlertStatus }) {
  return <Badge className={alertStatusStyles[status]}>{alertStatusLabels[status]}</Badge>;
}

const caseStatusStyles: Record<CaseStatus, string> = {
  open: "border-cyan-dim/60 text-cyan bg-cyan-dim/10",
  investigating: "border-amber-dim/60 text-amber/80 bg-amber-dim/10",
  contained: "border-amber/50 text-amber bg-amber-dim/20",
  closed: "border-line text-mist bg-surface-raised",
};

export function CaseStatusBadge({ status }: { status: CaseStatus }) {
  return <Badge className={caseStatusStyles[status]}>{status}</Badge>;
}

const reputationStyles: Record<string, string> = {
  malicious: "border-threat/60 text-threat bg-threat-dim/20",
  suspicious: "border-amber-dim/60 text-amber/80 bg-amber-dim/10",
  clean: "border-cyan-dim/60 text-cyan bg-cyan-dim/10",
  unknown: "border-line text-mist bg-surface-raised",
};

export function ReputationBadge({ reputation }: { reputation: string | null }) {
  const key = reputation ?? "unknown";
  return (
    <Badge className={reputationStyles[key] ?? reputationStyles.unknown}>
      {reputation === "malicious" && (
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-threat" />
      )}
      {reputation ?? "pending"}
    </Badge>
  );
}
