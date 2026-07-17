"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface ReadinessResponse {
  status: string;
  database: string;
  redis: string;
}

export default function LandingPage() {
  // Unauthenticated on purpose: this is the pre-login gateway, so the one
  // live signal it can honestly show is the public health check — the
  // richer stats (alert counts, MITRE coverage) live behind auth on the
  // dashboard now that RBAC guards the metrics endpoints.
  const health = useQuery({
    queryKey: ["health", "ready"],
    queryFn: () => api.get<ReadinessResponse>("/health/ready"),
    retry: false,
    refetchInterval: 30_000,
  });

  const isLive = health.data?.status === "ok";

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-void px-6">
      <div className="pointer-events-none absolute inset-0 bg-signature-grid opacity-40 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-1/3 animate-scan bg-gradient-to-b from-cyan/10 via-cyan/0 to-transparent"
        aria-hidden
      />

      <div className="relative z-10 flex max-w-2xl flex-col items-center text-center">
        <span className="font-mono text-xs uppercase tracking-[0.3em] text-mist">
          AI SOC analyst copilot
        </span>

        <h1 className="mt-6 font-display text-6xl italic tracking-tight text-paper sm:text-7xl">
          Sentris
        </h1>

        <p className="mt-6 max-w-lg text-balance text-lg leading-relaxed text-mist">
          An alert lands. Sentris explains what happened, enriches every indicator, maps it to
          MITRE ATT&CK, and drafts the incident report — before an analyst finishes reading the
          title.
        </p>

        <Link
          href="/login"
          className="mt-10 inline-flex items-center gap-2 rounded-md bg-cyan px-6 py-3 text-sm font-medium text-void transition-colors hover:bg-cyan/90"
        >
          Sign in to the console
        </Link>

        <div className="mt-8 flex items-center gap-2 border-t border-line pt-6 font-mono text-[11px] text-mist">
          <span className="relative flex h-2 w-2">
            {isLive && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan opacity-40" />
            )}
            <span
              className={`relative inline-flex h-2 w-2 rounded-full ${isLive ? "bg-cyan" : "bg-mist"}`}
            />
          </span>
          {isLive
            ? "System live — database & queue connected"
            : health.isLoading
              ? "Checking system status…"
              : "System unreachable"}
        </div>
      </div>
    </main>
  );
}
