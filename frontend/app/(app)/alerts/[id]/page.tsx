"use client";

import { useParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardHeader } from "@/components/ui/card";
import { AlertStatusBadge, ReputationBadge, SeverityBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAlert } from "@/lib/queries";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { AIAnalysis, AlertStatus } from "@/lib/types";

function latestByTask(analyses: AIAnalysis[], task: string): AIAnalysis | undefined {
  return analyses.find((a) => a.task === task);
}

function AIActionButton({
  label,
  pending,
  onClick,
}: {
  label: string;
  pending: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={pending}
      className="rounded-md border border-line px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-mist transition-colors hover:border-cyan hover:text-cyan disabled:opacity-40"
    >
      {pending ? "Working…" : label}
    </button>
  );
}

const STATUS_FLOW: AlertStatus[] = [
  "new",
  "triaging",
  "investigating",
  "closed",
  "false_positive",
];

export default function AlertDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: alert, isLoading } = useAlert(params.id);
  const queryClient = useQueryClient();

  const updateStatus = useMutation({
    mutationFn: (status: AlertStatus) => api.patch(`/alerts/${params.id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert", params.id] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const reEnrich = useMutation({
    mutationFn: () => api.post(`/alerts/${params.id}/enrich`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert", params.id] });
    },
  });

  const invalidateAlert = () => {
    queryClient.invalidateQueries({ queryKey: ["alert", params.id] });
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
  };

  const summarize = useMutation({
    mutationFn: () => api.post(`/ai/alerts/${params.id}/summarize`, {}),
    onSuccess: invalidateAlert,
  });
  const triage = useMutation({
    mutationFn: () => api.post(`/ai/alerts/${params.id}/triage`, {}),
    onSuccess: invalidateAlert,
  });
  const investigate = useMutation({
    mutationFn: () => api.post(`/ai/alerts/${params.id}/investigate`, {}),
    onSuccess: invalidateAlert,
  });
  const mapMitre = useMutation({
    mutationFn: () => api.post(`/ai/alerts/${params.id}/mitre`, {}),
    onSuccess: invalidateAlert,
  });

  const aiError = [summarize, triage, investigate, mapMitre].find((m) => m.isError)?.error;
  const aiErrorMessage =
    aiError instanceof ApiError
      ? aiError.status === 503
        ? "AI is unavailable — configure a free NVIDIA NIM/Groq/OpenRouter key or run Ollama locally."
        : aiError.message
      : null;

  if (isLoading || !alert) {
    return (
      <div>
        <Topbar title="Alert" />
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
        title={alert.title}
        description={`${alert.source} · ${alert.rule_name ?? "no rule"}`}
        action={
          <div className="flex items-center gap-3">
            <SeverityBadge severity={alert.severity} />
            <select
              value={alert.status}
              onChange={(e) => updateStatus.mutate(e.target.value as AlertStatus)}
              className="rounded-md border border-line bg-surface px-3 py-1.5 text-sm text-paper focus:border-cyan"
            >
              {STATUS_FLOW.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-5 p-8 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardHeader eyebrow="MITRE ATT&CK" title="Technique mapping" />
            <div className="p-5">
              {alert.mitre.length === 0 ? (
                <p className="text-sm text-mist">
                  No techniques mapped yet. The AI-based mapper arrives in a later phase.
                </p>
              ) : (
                <ul className="space-y-2">
                  {alert.mitre.map((m) => (
                    <li
                      key={m.technique.id}
                      className="flex items-center justify-between rounded-md border border-line px-3 py-2"
                    >
                      <div>
                        <span className="font-mono text-xs text-cyan">{m.technique.id}</span>
                        <span className="ml-2 text-sm text-paper">{m.technique.name}</span>
                      </div>
                      <span className="font-mono text-[11px] uppercase text-mist">
                        {m.source}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader
              eyebrow="Copilot"
              title="AI analysis"
              action={
                <div className="flex flex-wrap justify-end gap-2">
                  <AIActionButton
                    label="Summarize"
                    pending={summarize.isPending}
                    onClick={() => summarize.mutate()}
                  />
                  <AIActionButton
                    label="Triage"
                    pending={triage.isPending}
                    onClick={() => triage.mutate()}
                  />
                  <AIActionButton
                    label="Investigate"
                    pending={investigate.isPending}
                    onClick={() => investigate.mutate()}
                  />
                  <AIActionButton
                    label="Map MITRE"
                    pending={mapMitre.isPending}
                    onClick={() => mapMitre.mutate()}
                  />
                </div>
              }
            />
            <div className="space-y-4 p-5">
              {aiErrorMessage && (
                <p className="rounded-md border border-threat/40 bg-threat-dim/10 px-3 py-2 text-xs text-threat">
                  {aiErrorMessage}
                </p>
              )}

              {(() => {
                const summary = latestByTask(alert.ai_analyses, "summary");
                return summary ? (
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-wider text-mist">
                      Summary
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-paper">
                      {String(summary.output.summary ?? "")}
                    </p>
                  </div>
                ) : null;
              })()}

              {(() => {
                const triageResult = latestByTask(alert.ai_analyses, "triage");
                if (!triageResult) return null;
                const output = triageResult.output as {
                  severity?: string;
                  priority?: number;
                  reasoning?: string;
                };
                return (
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-wider text-mist">
                      Triage
                    </p>
                    <div className="mt-1 flex items-center gap-3">
                      <span className="rounded-full border border-amber-dim/60 bg-amber-dim/10 px-2.5 py-0.5 font-mono text-[11px] uppercase text-amber/80">
                        {output.severity}
                      </span>
                      <span className="font-mono text-xs text-mist">
                        priority {output.priority}/100
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-paper">{output.reasoning}</p>
                  </div>
                );
              })()}

              {(() => {
                const steps = latestByTask(alert.ai_analyses, "steps");
                if (!steps) return null;
                const output = steps.output as { steps?: string[] };
                return (
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-wider text-mist">
                      Investigation steps
                    </p>
                    <ol className="mt-1 list-decimal space-y-1 pl-4 text-sm text-paper">
                      {(output.steps ?? []).map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>
                );
              })()}

              {alert.ai_analyses.length === 0 && !aiErrorMessage && (
                <p className="text-sm text-mist">
                  No AI analysis yet — use the buttons above to summarize, triage, investigate,
                  or map this alert to MITRE ATT&CK with the LLM copilot.
                </p>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader eyebrow="Raw" title="Source payload" />
            <pre className="overflow-x-auto p-5 font-mono text-xs text-mist">
              {JSON.stringify(alert.raw, null, 2)}
            </pre>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader eyebrow="Detail" title="Overview" />
            <dl className="divide-y divide-line px-5">
              {[
                ["Status", <AlertStatusBadge key="s" status={alert.status} />],
                ["Source", alert.source],
                ["Rule", alert.rule_name ?? "—"],
                ["Src IP", alert.src_ip ?? "—"],
                ["Dst IP", alert.dst_ip ?? "—"],
                ["User", alert.user_subject ?? "—"],
                [
                  "AI severity",
                  alert.ai_severity ? (
                    <SeverityBadge key="ais" severity={alert.ai_severity} />
                  ) : (
                    "—"
                  ),
                ],
                ["AI priority", alert.priority != null ? `${alert.priority}/100` : "—"],
                ["Occurred", formatDateTime(alert.occurred_at)],
                ["Ingested", formatDateTime(alert.ingested_at)],
              ].map(([label, value]) => (
                <div key={label as string} className="flex items-center justify-between py-2.5 text-sm">
                  <dt className="text-mist">{label}</dt>
                  <dd className="font-mono text-xs text-paper">{value}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card>
            <CardHeader
              eyebrow={`${alert.iocs.length} linked`}
              title="Indicators"
              action={
                <button
                  onClick={() => reEnrich.mutate()}
                  disabled={reEnrich.isPending || alert.iocs.length === 0}
                  className="rounded-md border border-line px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider text-mist transition-colors hover:border-cyan hover:text-cyan disabled:opacity-40"
                >
                  {reEnrich.isPending ? "Enriching…" : "Re-enrich"}
                </button>
              }
            />
            <div className="space-y-3 p-5">
              {alert.iocs.length === 0 && (
                <p className="text-sm text-mist">No indicators extracted from this alert.</p>
              )}
              {alert.iocs.map((ioc) => (
                <div key={ioc.id} className="rounded-md border border-line p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-paper">{ioc.value}</span>
                    <span className="font-mono text-[10px] uppercase text-mist">{ioc.type}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <ReputationBadge reputation={ioc.reputation} />
                    {ioc.enrichments.length > 0 && (
                      <span className="font-mono text-[10px] text-mist">
                        {ioc.enrichments
                          .map((e) => `${e.provider}:${e.verdict ?? "unknown"}`)
                          .join(" · ")}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
