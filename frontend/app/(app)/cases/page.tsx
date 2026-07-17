"use client";

import { useState } from "react";
import Link from "next/link";
import { Topbar } from "@/components/layout/topbar";
import { Card } from "@/components/ui/card";
import { CaseStatusBadge, SeverityBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useCases } from "@/lib/queries";
import { formatDateTime } from "@/lib/utils";
import type { CaseStatus } from "@/lib/types";

const STATUS_OPTIONS: (CaseStatus | "")[] = ["", "open", "investigating", "contained", "closed"];

export default function CasesPage() {
  const [status, setStatus] = useState<CaseStatus | "">("");
  const cases = useCases({ status });

  return (
    <div>
      <Topbar title="Cases" description="Alerts promoted into an investigation." />

      <div className="p-8">
        <div className="mb-4 flex items-center gap-3">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as CaseStatus | "")}
            className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-paper focus:border-cyan"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === "" ? "All statuses" : opt}
              </option>
            ))}
          </select>
        </div>

        <Card className="overflow-x-auto">
          <div className="min-w-[560px]">
            <div className="grid grid-cols-[1fr_120px_140px_160px] gap-4 border-b border-line px-5 py-3 font-mono text-[11px] uppercase tracking-wider text-mist">
              <span>Title</span>
              <span>Severity</span>
              <span>Status</span>
              <span>Opened</span>
            </div>
            <div className="divide-y divide-line">
              {cases.isLoading &&
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="px-5 py-4">
                    <Skeleton className="h-4 w-3/4" />
                  </div>
                ))}
              {cases.data?.items.length === 0 && (
                <div className="px-5 py-10 text-center text-sm text-mist">
                  No cases yet. Promote an alert from its detail page to start one.
                </div>
              )}
              {cases.data?.items.map((c) => (
                <Link
                  key={c.id}
                  href={`/cases/${c.id}`}
                  className="grid grid-cols-[1fr_120px_140px_160px] items-center gap-4 px-5 py-3.5 text-sm transition-colors hover:bg-surface-raised"
                >
                  <span className="truncate text-paper">{c.title}</span>
                  <SeverityBadge severity={c.severity} />
                  <CaseStatusBadge status={c.status} />
                  <span className="font-mono text-xs text-mist">
                    {formatDateTime(c.opened_at)}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
