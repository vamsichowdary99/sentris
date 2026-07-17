"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertStatusBadge, CaseStatusBadge, SeverityBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useCase, useCaseReports } from "@/lib/queries";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatRelativeTime } from "@/lib/utils";
import type { CaseStatus } from "@/lib/types";

const STATUS_FLOW: CaseStatus[] = ["open", "investigating", "contained", "closed"];

const TIMELINE_LABEL: Record<string, string> = {
  case_opened: "Case opened",
  alert_linked: "Alert linked",
  status_changed: "Status changed",
  comment_added: "Comment added",
};

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: caseDetail, isLoading } = useCase(params.id);
  const { data: reports } = useCaseReports(params.id);
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["case", params.id] });

  const generateReport = useMutation({
    mutationFn: () => api.post(`/ai/cases/${params.id}/report`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["case", params.id, "reports"] }),
  });
  const reportError =
    generateReport.error instanceof ApiError
      ? generateReport.error.status === 503
        ? "AI is unavailable — configure a free NVIDIA NIM/Groq/OpenRouter key or run Ollama locally."
        : generateReport.error.message
      : null;

  const updateStatus = useMutation({
    mutationFn: (status: CaseStatus) => api.patch(`/cases/${params.id}`, { status }),
    onSuccess: invalidate,
  });

  const addComment = useMutation({
    mutationFn: (body: string) => api.post(`/cases/${params.id}/comments`, { body }),
    onSuccess: () => {
      setComment("");
      invalidate();
    },
  });

  if (isLoading || !caseDetail) {
    return (
      <div>
        <Topbar title="Case" />
        <div className="space-y-4 p-8">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Topbar
        title={caseDetail.title}
        description={caseDetail.summary ?? undefined}
        action={
          <div className="flex items-center gap-3">
            <SeverityBadge severity={caseDetail.severity} />
            <select
              value={caseDetail.status}
              onChange={(e) => updateStatus.mutate(e.target.value as CaseStatus)}
              className="rounded-md border border-line bg-surface px-3 py-1.5 text-sm text-paper focus:border-cyan"
            >
              {STATUS_FLOW.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-5 p-8 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardHeader eyebrow={`${caseDetail.alerts.length} linked`} title="Alerts" />
            <div className="divide-y divide-line">
              {caseDetail.alerts.length === 0 && (
                <p className="p-5 text-sm text-mist">No alerts linked to this case yet.</p>
              )}
              {caseDetail.alerts.map((alert) => (
                <Link
                  key={alert.id}
                  href={`/alerts/${alert.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-3.5 text-sm transition-colors hover:bg-surface-raised"
                >
                  <span className="truncate text-paper">{alert.title}</span>
                  <div className="flex shrink-0 items-center gap-3">
                    <SeverityBadge severity={alert.severity} />
                    <AlertStatusBadge status={alert.status} />
                  </div>
                </Link>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader eyebrow="Discussion" title="Comments" />
            <div className="space-y-3 p-5">
              {caseDetail.comments.length === 0 && (
                <p className="text-sm text-mist">No comments yet.</p>
              )}
              {caseDetail.comments.map((c) => (
                <div key={c.id} className="rounded-md border border-line p-3">
                  <p className="text-sm text-paper">{c.body}</p>
                  <p className="mt-1 font-mono text-[11px] text-mist">
                    {formatRelativeTime(c.created_at)}
                  </p>
                </div>
              ))}
              <div className="flex gap-2 pt-1">
                <input
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Add a comment…"
                  className="flex-1 rounded-md border border-line bg-surface-raised px-3 py-2 text-sm text-paper placeholder:text-mist focus:border-cyan"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && comment.trim()) addComment.mutate(comment.trim());
                  }}
                />
                <Button
                  variant="outline"
                  disabled={!comment.trim() || addComment.isPending}
                  onClick={() => comment.trim() && addComment.mutate(comment.trim())}
                >
                  Post
                </Button>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              eyebrow="Copilot"
              title="Incident report"
              action={
                <Button
                  variant="outline"
                  disabled={generateReport.isPending}
                  onClick={() => generateReport.mutate()}
                >
                  {generateReport.isPending
                    ? "Generating…"
                    : reports && reports.length > 0
                      ? "Regenerate"
                      : "Generate report"}
                </Button>
              }
            />
            <div className="space-y-3 p-5">
              {reportError && (
                <p className="rounded-md border border-threat/40 bg-threat-dim/10 px-3 py-2 text-xs text-threat">
                  {reportError}
                </p>
              )}
              {(() => {
                const latestReport = reports?.[0] ?? null;
                if (!latestReport) {
                  return (
                    <p className="text-sm text-mist">
                      No report yet — generate a full incident report from this case&apos;s alerts,
                      indicators, and timeline with one click.
                    </p>
                  );
                }
                return (
                  <>
                    <p className="font-mono text-[11px] text-mist">
                      Latest — {formatRelativeTime(latestReport.created_at)}
                    </p>
                    <pre className="max-h-[32rem] overflow-y-auto overflow-x-auto whitespace-pre-wrap rounded-md bg-surface-raised p-4 font-mono text-xs leading-relaxed text-paper">
                      {latestReport.content}
                    </pre>
                    {reports && reports.length > 1 && (
                      <p className="font-mono text-[11px] text-mist">
                        {reports.length - 1} earlier version(s) generated
                      </p>
                    )}
                  </>
                );
              })()}
            </div>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader eyebrow="Detail" title="Overview" />
            <dl className="divide-y divide-line px-5">
              {[
                ["Status", <CaseStatusBadge key="s" status={caseDetail.status} />],
                ["Opened", formatDateTime(caseDetail.opened_at)],
                ["Closed", caseDetail.closed_at ? formatDateTime(caseDetail.closed_at) : "—"],
              ].map(([label, value]) => (
                <div
                  key={label as string}
                  className="flex items-center justify-between py-2.5 text-sm"
                >
                  <dt className="text-mist">{label}</dt>
                  <dd className="font-mono text-xs text-paper">{value}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card>
            <CardHeader eyebrow="History" title="Timeline" />
            <ol className="space-y-4 p-5">
              {caseDetail.timeline.map((event) => (
                <li key={event.id} className="flex gap-3">
                  <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" />
                  <div>
                    <p className="text-sm text-paper">
                      {TIMELINE_LABEL[event.kind] ?? event.kind}
                    </p>
                    <p className="text-xs text-mist">{event.description}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-mist">
                      {formatRelativeTime(event.ts)}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
    </div>
  );
}
