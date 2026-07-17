"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Clock, Loader2, ScanSearch, Sparkles } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertStatusBadge, ReputationBadge, SeverityBadge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";
import type {
  IntegrationStatus,
  InvestigateDetailResponse,
  InvestigateReportResponse,
  InvestigateResponse,
  IOCType,
  ProviderOutcome,
} from "@/lib/types";

const TYPE_LABELS: Record<IOCType, string> = {
  ip: "IP address",
  domain: "domain",
  url: "URL",
  hash: "file hash",
};

const STATUS_LABELS: Record<ProviderOutcome["status"], string> = {
  ok: "fresh",
  cached: "cached",
  timeout: "timed out",
  error: "unavailable",
  misconfigured: "check API key",
  rate_limited: "rate limited",
  scanning: "scanning…",
};

const PROVIDER_LABELS: Record<string, string> = {
  virustotal: "VirusTotal",
  abuseipdb: "AbuseIPDB",
  shodan: "Shodan",
  otx: "AlienVault OTX",
  greynoise: "GreyNoise",
  abusech: "abuse.ch",
  urlscan: "urlscan.io",
  whois: "WHOIS / RDAP",
};

function providerHighlights(provider: string, raw: Record<string, unknown>): [string, string][] {
  const s = (v: unknown) => (v === null || v === undefined ? "—" : String(v));
  const list = (v: unknown) => (Array.isArray(v) && v.length > 0 ? v.join(", ") : "none");

  switch (provider) {
    case "virustotal": {
      const stats = (raw.last_analysis_stats ?? {}) as Record<string, number>;
      const total = Object.values(stats).reduce((a, b) => a + b, 0);
      return [["Engines flagged malicious", `${stats.malicious ?? 0} / ${total || "—"}`]];
    }
    case "abuseipdb":
      return [
        ["Abuse confidence", `${s(raw.abuseConfidenceScore)}%`],
        ["Reports", s(raw.totalReports)],
        ["ISP", s(raw.isp)],
      ];
    case "shodan":
      return [
        ["Open ports", list(raw.ports)],
        ["Known CVEs", list(raw.vulns)],
        ["Org", s(raw.org)],
      ];
    case "otx":
      return [
        ["Pulses", s(raw.pulse_count)],
        ["Malware families", list(raw.malware_families)],
        ["Adversary", s(raw.adversary)],
        ["Campaign", s(raw.campaign)],
      ];
    case "greynoise":
      return [
        ["Classification", s(raw.classification)],
        ["Internet-wide scanner?", raw.noise ? "Yes" : "No"],
        ["Tags", list(raw.tags)],
      ];
    case "abusech":
      return raw.found
        ? [
            ["Malware family", s(raw.malware_family)],
            ["Confidence", s(raw.confidence_level)],
          ]
        : [["Found", "No match in ThreatFox/MalwareBazaar"]];
    case "urlscan":
      if (raw.scan_status === "in_progress") {
        return [["Status", "Scan submitted, not ready yet"]];
      }
      if (raw.scan_status === "complete") {
        return [
          ["Domain", s(raw.domain)],
          ["Server", s(raw.server)],
          ["IP", s(raw.ip)],
        ];
      }
      return [["Found", "No scan on record"]];
    case "whois":
      return [
        [
          "Domain age",
          raw.domain_age_days != null ? `${raw.domain_age_days} days` : "unknown",
        ],
      ];
    default:
      return Object.entries(raw)
        .slice(0, 4)
        .map(([k, v]): [string, string] => [k, s(v)]);
  }
}

export default function InvestigatePage() {
  const [indicator, setIndicator] = useState("");
  const [detail, setDetail] = useState<InvestigateDetailResponse | null>(null);
  const [report, setReport] = useState<InvestigateReportResponse | null>(null);

  const integrationStatus = useQuery({
    queryKey: ["integrations", "status"],
    queryFn: () => api.get<IntegrationStatus[]>("/integrations/status"),
    staleTime: 30_000,
  });

  const investigateMutation = useMutation({
    mutationFn: async (value: string) => {
      const resp = await api.post<InvestigateResponse>("/investigate", { indicator: value });
      return api.get<InvestigateDetailResponse>(`/investigate/${resp.ioc.id}`);
    },
    onSuccess: (data) => {
      setDetail(data);
      setReport(null);
    },
  });

  const refreshMutation = useMutation({
    mutationFn: async () => {
      if (!detail) throw new Error("nothing to refresh");
      await api.post<InvestigateResponse>(`/investigate/${detail.ioc.id}/refresh`, {});
      return api.get<InvestigateDetailResponse>(`/investigate/${detail.ioc.id}`);
    },
    onSuccess: setDetail,
  });

  const reportMutation = useMutation({
    mutationFn: async () => {
      if (!detail) throw new Error("nothing to report on");
      return api.post<InvestigateReportResponse>("/investigate/report", {
        ioc_id: detail.ioc.id,
      });
    },
    onSuccess: setReport,
  });

  const investigateError =
    investigateMutation.error instanceof ApiError ? investigateMutation.error.message : null;
  const reportError =
    reportMutation.error instanceof ApiError
      ? reportMutation.error.status === 503
        ? "AI is unavailable — configure a free NVIDIA NIM/Groq/OpenRouter key or run Ollama locally."
        : reportMutation.error.message
      : null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (indicator.trim()) investigateMutation.mutate(indicator.trim());
  }

  return (
    <div>
      <Topbar
        title="Investigate"
        description="Paste any IP, domain, URL, or file hash — Sentris fans out to every threat-intel source in parallel and synthesizes a verdict."
      />

      <div className="mx-auto max-w-4xl space-y-6 p-8">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <ScanSearch
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-mist"
            />
            <input
              value={indicator}
              onChange={(e) => setIndicator(e.target.value)}
              placeholder="185.220.101.45, secure-office365-login.com, or a SHA256 hash…"
              className="w-full rounded-md border border-line bg-surface py-3 pl-9 pr-3 font-mono text-sm text-paper placeholder:text-mist focus:border-cyan"
            />
          </div>
          <Button type="submit" disabled={investigateMutation.isPending || !indicator.trim()}>
            {investigateMutation.isPending ? "Investigating…" : "Investigate"}
          </Button>
        </form>

        {investigateError && (
          <p className="rounded-md border border-threat/40 bg-threat-dim/10 px-3 py-2 text-xs text-threat">
            {investigateError}
          </p>
        )}

        {integrationStatus.data && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-[11px] text-mist">
            <span className="uppercase tracking-wider">Sources:</span>
            {integrationStatus.data.map((s) => (
              <span key={s.provider} className="flex items-center gap-1">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    s.mode === "live" ? "bg-cyan" : "bg-mist/50"
                  }`}
                />
                {PROVIDER_LABELS[s.provider] ?? s.provider}
                <span className="text-mist/60">({s.mode})</span>
              </span>
            ))}
          </div>
        )}

        {detail && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-cyan-dim/60 bg-cyan-dim/10 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-cyan">
                Detected: {TYPE_LABELS[detail.detected_type]}
              </span>
              <span className="font-mono text-xs text-mist">{detail.ioc.value}</span>
              <ReputationBadge reputation={detail.ioc.reputation} />
              <button
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending}
                className="ml-auto rounded-md border border-line px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider text-mist transition-colors hover:border-cyan hover:text-cyan disabled:opacity-40"
              >
                {refreshMutation.isPending ? "Refreshing…" : "Re-run (bypass cache)"}
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {detail.providers.map((p) => {
                const needsAttention =
                  p.status === "timeout" ||
                  p.status === "error" ||
                  p.status === "misconfigured" ||
                  p.status === "rate_limited";
                return (
                  <Card key={p.provider} className="p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-display text-sm text-paper">
                        {PROVIDER_LABELS[p.provider] ?? p.provider}
                      </span>
                      {p.status === "scanning" ? (
                        <span className="flex items-center gap-1 font-mono text-[10px] uppercase text-cyan">
                          <Loader2 size={11} className="animate-spin" /> {STATUS_LABELS[p.status]}
                        </span>
                      ) : needsAttention ? (
                        <span className="flex items-center gap-1 font-mono text-[10px] uppercase text-mist">
                          <AlertTriangle size={11} /> {STATUS_LABELS[p.status]}
                        </span>
                      ) : (
                        <ReputationBadge reputation={p.verdict} />
                      )}
                    </div>
                    {p.status === "rate_limited" && (
                      <p className="mt-2 flex items-center gap-1 font-mono text-[10px] text-mist">
                        <Clock size={11} />
                        retry in {Math.max(1, Math.round(Number(p.raw.retry_after_seconds) || 60))}s
                      </p>
                    )}
                    {p.status === "misconfigured" && (
                      <p className="mt-2 text-xs text-mist">
                        This source&apos;s API key looks invalid or expired.
                      </p>
                    )}
                    {p.status !== "rate_limited" && p.status !== "misconfigured" && (
                      <dl className="mt-3 space-y-1.5">
                        {providerHighlights(p.provider, p.raw).map(([label, value]) => (
                          <div
                            key={label}
                            className="flex items-center justify-between gap-3 text-xs"
                          >
                            <dt className="shrink-0 text-mist">{label}</dt>
                            <dd className="truncate text-right font-mono text-paper">{value}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                    {p.provider === "urlscan" &&
                      p.raw.scan_status === "complete" &&
                      typeof p.raw.screenshot_url === "string" && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={p.raw.screenshot_url}
                          alt={`urlscan.io screenshot of ${detail.ioc.value}`}
                          className="mt-3 w-full rounded-md border border-line"
                        />
                      )}
                    {p.fetched_at && (
                      <p className="mt-3 font-mono text-[10px] text-mist">
                        {p.status === "cached" ? "cached" : "fetched"}{" "}
                        {formatRelativeTime(p.fetched_at)}
                      </p>
                    )}
                  </Card>
                );
              })}
            </div>

            {(detail.related_alerts.length > 0 || detail.related_cases.length > 0) && (
              <Card>
                <CardHeader eyebrow="Pivot" title="Related in Sentris" />
                <div className="space-y-2 p-5">
                  {detail.related_alerts.map((a) => (
                    <Link
                      key={a.id}
                      href={`/alerts/${a.id}`}
                      className="flex items-center justify-between gap-3 rounded-md border border-line px-3 py-2 text-sm transition-colors hover:bg-surface-raised"
                    >
                      <span className="truncate text-paper">{a.title}</span>
                      <div className="flex shrink-0 items-center gap-2">
                        <SeverityBadge severity={a.severity} />
                        <AlertStatusBadge status={a.status} />
                      </div>
                    </Link>
                  ))}
                  {detail.related_cases.map((c) => (
                    <Link
                      key={c.id}
                      href={`/cases/${c.id}`}
                      className="flex items-center justify-between gap-3 rounded-md border border-line px-3 py-2 text-sm transition-colors hover:bg-surface-raised"
                    >
                      <span className="truncate text-paper">{c.title}</span>
                      <SeverityBadge severity={c.severity} />
                    </Link>
                  ))}
                </div>
              </Card>
            )}

            <Card>
              <CardHeader
                eyebrow="Copilot"
                title="AI investigation report"
                action={
                  <Button
                    variant="outline"
                    disabled={reportMutation.isPending}
                    onClick={() => reportMutation.mutate()}
                  >
                    <Sparkles size={14} />
                    {reportMutation.isPending
                      ? "Synthesizing…"
                      : report
                        ? "Regenerate"
                        : "Generate report"}
                  </Button>
                }
              />
              <div className="space-y-5 p-5">
                {reportError && (
                  <p className="rounded-md border border-threat/40 bg-threat-dim/10 px-3 py-2 text-xs text-threat">
                    {reportError}
                  </p>
                )}
                {!report && !reportError && (
                  <p className="text-sm text-mist">
                    Generate a synthesized verdict across every source above, with attribution,
                    conflict reconciliation, and recommended actions.
                  </p>
                )}
                {report && (
                  <>
                    <div className="flex items-center gap-3">
                      <ReputationBadge
                        reputation={
                          report.report.verdict === "benign" ? "clean" : report.report.verdict
                        }
                      />
                      <span className="font-mono text-xs text-mist">
                        confidence {Math.round(report.report.confidence * 100)}%
                      </span>
                    </div>
                    <p className="text-sm text-paper">{report.report.rationale}</p>

                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-wider text-mist">
                        Attribution
                      </p>
                      <p className="mt-1 text-sm text-paper">
                        {report.report.attribution.malware_family ||
                        report.report.attribution.campaign ||
                        report.report.attribution.threat_actor ? (
                          <>
                            {[
                              report.report.attribution.malware_family,
                              report.report.attribution.campaign,
                              report.report.attribution.threat_actor,
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                            {" — "}
                          </>
                        ) : null}
                        {report.report.attribution.summary}
                      </p>
                    </div>

                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-wider text-mist">
                        Evidence
                      </p>
                      <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-paper">
                        {report.report.evidence.map((e, i) => (
                          <li key={i}>{e}</li>
                        ))}
                      </ul>
                    </div>

                    {report.report.conflicts.length > 0 && (
                      <div className="rounded-md border border-amber/50 bg-amber-dim/10 p-3">
                        <p className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-amber">
                          <AlertTriangle size={12} /> Source conflict
                        </p>
                        <ul className="mt-1.5 list-disc space-y-1 pl-4 text-sm text-paper">
                          {report.report.conflicts.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-wider text-mist">
                        Recommended actions
                      </p>
                      <ul className="mt-1 space-y-1.5 text-sm text-paper">
                        {report.report.recommended_actions.map((a, i) => (
                          <li key={i}>
                            <span className="text-paper">{a.action}</span>{" "}
                            <span className="text-mist">— {a.rationale}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </>
                )}
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
