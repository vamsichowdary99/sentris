"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Sparkles, X } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Card } from "@/components/ui/card";
import { AlertStatusBadge, SeverityBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAlerts } from "@/lib/queries";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { Alert, AlertStatus, NLSearchResponse, Severity } from "@/lib/types";

const STATUS_OPTIONS: (AlertStatus | "")[] = [
  "",
  "new",
  "triaging",
  "investigating",
  "closed",
  "false_positive",
];
const SEVERITY_OPTIONS: (Severity | "")[] = ["", "critical", "high", "medium", "low", "info"];
const GRID_COLS = "grid-cols-[1fr_80px_110px_140px_100px_140px]";

export default function AlertsPage() {
  const [status, setStatus] = useState<AlertStatus | "">("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [aiQuery, setAiQuery] = useState("");
  const [aiResult, setAiResult] = useState<NLSearchResponse | null>(null);
  const queryClient = useQueryClient();

  const alerts = useAlerts({ status, severity, q, page, size: 20 });
  const totalPages = alerts.data ? Math.max(1, Math.ceil(alerts.data.total / 20)) : 1;

  const nlSearch = useMutation({
    mutationFn: (query: string) => api.post<NLSearchResponse>("/ai/search", { query }),
    onSuccess: setAiResult,
  });
  const nlSearchErrorMessage =
    nlSearch.error instanceof ApiError
      ? nlSearch.error.status === 503
        ? "AI is unavailable — configure a free NVIDIA NIM/Groq/OpenRouter key or run Ollama locally."
        : nlSearch.error.message
      : null;

  const visibleAlerts: Alert[] = aiResult ? aiResult.items : (alerts.data?.items ?? []);

  const prioritize = useMutation({
    mutationFn: () =>
      api.post("/ai/alerts/summarize-batch", {
        alert_ids: visibleAlerts.slice(0, 30).map((a) => a.id),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      if (aiQuery.trim()) nlSearch.mutate(aiQuery.trim());
    },
  });
  const prioritizeErrorMessage =
    prioritize.error instanceof ApiError
      ? prioritize.error.status === 503
        ? "AI is unavailable — configure a free NVIDIA NIM/Groq/OpenRouter key or run Ollama locally."
        : prioritize.error.message
      : null;

  return (
    <div>
      <Topbar title="Alerts" description="Every alert ingested, filterable by status and severity." />

      <div className="p-8">
        <div className="mb-3 flex items-center gap-2 rounded-md border border-cyan-dim/40 bg-cyan-dim/5 px-3 py-2">
          <Sparkles size={15} className="shrink-0 text-cyan" />
          <input
            value={aiQuery}
            onChange={(e) => setAiQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && aiQuery.trim()) nlSearch.mutate(aiQuery.trim());
            }}
            placeholder='Ask AI — "critical alerts from wazuh in the last day"'
            className="flex-1 bg-transparent text-sm text-paper placeholder:text-mist focus:outline-none"
          />
          {aiResult && (
            <button
              onClick={() => {
                setAiResult(null);
                setAiQuery("");
              }}
              className="flex items-center gap-1 rounded-md px-2 py-1 font-mono text-[11px] uppercase text-mist hover:text-paper"
            >
              <X size={12} /> clear
            </button>
          )}
          <button
            onClick={() => aiQuery.trim() && nlSearch.mutate(aiQuery.trim())}
            disabled={nlSearch.isPending || !aiQuery.trim()}
            className="rounded-md bg-cyan px-3 py-1 text-xs font-medium text-void hover:bg-cyan/90 disabled:opacity-40"
          >
            {nlSearch.isPending ? "Thinking…" : "Ask"}
          </button>
        </div>
        {nlSearchErrorMessage && (
          <p className="mb-3 rounded-md border border-threat/40 bg-threat-dim/10 px-3 py-2 text-xs text-threat">
            {nlSearchErrorMessage}
          </p>
        )}
        {aiResult && (
          <div className="mb-4 flex flex-wrap items-center gap-2 font-mono text-[11px] text-mist">
            <span className="text-cyan">applied filters:</span>
            {Object.entries(aiResult.filter)
              .filter(([, v]) => v)
              .map(([k, v]) => (
                <span key={k} className="rounded-full border border-line px-2 py-0.5">
                  {k}={String(v)}
                </span>
              ))}
            {Object.values(aiResult.filter).every((v) => !v) && <span>none — showing all</span>}
          </div>
        )}

        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-mist" />
            <input
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
                setAiResult(null);
              }}
              placeholder="Search titles…"
              className="w-full rounded-md border border-line bg-surface py-2 pl-9 pr-3 text-sm text-paper placeholder:text-mist focus:border-cyan"
            />
          </div>
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as AlertStatus | "");
              setPage(1);
              setAiResult(null);
            }}
            className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-paper focus:border-cyan"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === "" ? "All statuses" : opt.replace("_", " ")}
              </option>
            ))}
          </select>
          <select
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value as Severity | "");
              setPage(1);
              setAiResult(null);
            }}
            className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-paper focus:border-cyan"
          >
            {SEVERITY_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === "" ? "All severities" : opt}
              </option>
            ))}
          </select>
          <button
            onClick={() => prioritize.mutate()}
            disabled={prioritize.isPending || visibleAlerts.length === 0}
            className="ml-auto flex items-center gap-1.5 rounded-md border border-line px-3 py-2 text-xs font-medium text-mist transition-colors hover:border-cyan hover:text-cyan disabled:opacity-40"
          >
            <Sparkles size={13} />
            {prioritize.isPending ? "Prioritizing…" : "AI prioritize this view"}
          </button>
        </div>
        {prioritizeErrorMessage && (
          <p className="mb-4 rounded-md border border-threat/40 bg-threat-dim/10 px-3 py-2 text-xs text-threat">
            {prioritizeErrorMessage}
          </p>
        )}

        <Card className="overflow-x-auto">
          <div className="min-w-[820px]">
            <div
              className={`grid ${GRID_COLS} gap-4 border-b border-line px-5 py-3 font-mono text-[11px] uppercase tracking-wider text-mist`}
            >
              <span>Title</span>
              <span>AI</span>
              <span>Severity</span>
              <span>Status</span>
              <span>Source</span>
              <span>Occurred</span>
            </div>
            <div className="divide-y divide-line">
              {(alerts.isLoading || nlSearch.isPending) &&
                Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="px-5 py-4">
                    <Skeleton className="h-4 w-3/4" />
                  </div>
                ))}
              {!alerts.isLoading && !nlSearch.isPending && visibleAlerts.length === 0 && (
                <div className="px-5 py-10 text-center text-sm text-mist">
                  No alerts match these filters.
                </div>
              )}
              {!nlSearch.isPending &&
                visibleAlerts.map((alert) => (
                  <Link
                    key={alert.id}
                    href={`/alerts/${alert.id}`}
                    className={`grid ${GRID_COLS} items-center gap-4 px-5 py-3.5 text-sm transition-colors hover:bg-surface-raised`}
                  >
                    <span className="truncate text-paper">{alert.title}</span>
                    <span className="font-mono text-xs text-mist">
                      {alert.priority != null ? alert.priority : "—"}
                    </span>
                    <SeverityBadge severity={alert.ai_severity ?? alert.severity} />
                    <AlertStatusBadge status={alert.status} />
                    <span className="truncate font-mono text-xs text-mist">{alert.source}</span>
                    <span className="font-mono text-xs text-mist">
                      {formatDateTime(alert.occurred_at)}
                    </span>
                  </Link>
                ))}
            </div>
          </div>
        </Card>

        {!aiResult && alerts.data && totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between font-mono text-xs text-mist">
            <span>
              page {page} of {totalPages} · {alerts.data.total} alerts
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded border border-line px-3 py-1 disabled:opacity-40"
              >
                prev
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded border border-line px-3 py-1 disabled:opacity-40"
              >
                next
              </button>
            </div>
          </div>
        )}
        {aiResult && (
          <p className="mt-4 font-mono text-xs text-mist">
            {aiResult.total} matching alert(s) — showing up to {aiResult.items.length}
          </p>
        )}
      </div>
    </div>
  );
}
