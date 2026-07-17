"use client";

import Link from "next/link";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardHeader } from "@/components/ui/card";
import { SeverityBadge, AlertStatusBadge } from "@/components/ui/badge";
import { GridSkeleton, Skeleton } from "@/components/ui/skeleton";
import { LiveSignal } from "@/components/charts/live-signal";
import { SeverityDonut } from "@/components/charts/severity-donut";
import { MitreHeatmap } from "@/components/charts/mitre-heatmap";
import { useAlerts, useMetricsOverview, useMitreHeatmap, useMitreTechniques } from "@/lib/queries";
import { formatRelativeTime } from "@/lib/utils";

export default function DashboardPage() {
  const overview = useMetricsOverview();
  const alerts = useAlerts({ size: 50 });
  const heatmap = useMitreHeatmap();
  const techniques = useMitreTechniques();

  const recent = alerts.data?.items.slice(0, 6) ?? [];
  const criticalCount = overview.data?.alerts_by_severity.critical ?? 0;

  return (
    <div>
      <Topbar
        title="Dashboard"
        description="Live view of alert volume, severity mix, and ATT&CK coverage."
      />

      <div className="space-y-5 p-8">
        <Card>
          <div className="flex items-center justify-between px-5 pt-4">
            <div className="font-mono text-[11px] uppercase tracking-wider text-mist">
              Live signal · last 24h
            </div>
            <div className="flex items-center gap-4 font-mono text-xs">
              <span className="text-paper">{alerts.data?.total ?? "···"} total</span>
              {criticalCount > 0 && (
                <span className="text-threat">{criticalCount} critical</span>
              )}
            </div>
          </div>
          {alerts.isLoading ? (
            <div className="px-5 pb-4">
              <Skeleton className="h-16 w-full" />
            </div>
          ) : (
            <LiveSignal alerts={alerts.data?.items ?? []} />
          )}
        </Card>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">
          <Card className="lg:col-span-2">
            <CardHeader eyebrow="Triage" title="Severity mix" />
            <div className="p-5">
              {overview.isLoading ? (
                <Skeleton className="h-48 w-full" />
              ) : (
                <SeverityDonut counts={overview.data?.alerts_by_severity ?? {}} />
              )}
            </div>
          </Card>

          <Card className="lg:col-span-3">
            <CardHeader eyebrow="MITRE ATT&CK" title="Technique coverage" />
            <div className="p-5">
              {heatmap.isLoading || techniques.isLoading ? (
                <GridSkeleton rows={4} cols={14} />
              ) : (
                <MitreHeatmap
                  techniques={techniques.data?.items ?? []}
                  heatmap={heatmap.data ?? []}
                />
              )}
            </div>
          </Card>
        </div>

        <Card>
          <CardHeader
            eyebrow="Queue"
            title="Recent alerts"
            action={
              <Link href="/alerts" className="text-xs text-cyan hover:underline">
                View all →
              </Link>
            }
          />
          <div className="divide-y divide-line">
            {alerts.isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="px-5 py-4">
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ))}
            {recent.length === 0 && !alerts.isLoading && (
              <div className="px-5 py-10 text-center text-sm text-mist">
                No alerts yet. Run the seed script or the simulator to populate the queue.
              </div>
            )}
            {recent.map((alert) => (
              <Link
                key={alert.id}
                href={`/alerts/${alert.id}`}
                className="flex flex-col gap-2 px-5 py-3.5 transition-colors hover:bg-surface-raised sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <SeverityBadge severity={alert.severity} />
                  <span className="truncate text-sm text-paper">{alert.title}</span>
                </div>
                <div className="flex shrink-0 items-center gap-3 pl-1 sm:pl-0">
                  <AlertStatusBadge status={alert.status} />
                  <span className="font-mono text-xs text-mist">
                    {formatRelativeTime(alert.occurred_at)}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
