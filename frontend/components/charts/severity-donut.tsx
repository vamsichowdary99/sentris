"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { Severity } from "@/lib/types";

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "#E5484D",
  high: "#F5A623",
  medium: "#8A6220",
  low: "#4FD1E8",
  info: "#8B98A8",
};

export function SeverityDonut({ counts }: { counts: Record<string, number> }) {
  const data = SEVERITY_ORDER.map((severity) => ({
    name: severity,
    value: counts[severity] ?? 0,
  })).filter((d) => d.value > 0);

  const total = data.reduce((sum, d) => sum + d.value, 0);

  if (total === 0) {
    return (
      <div className="flex h-48 items-center justify-center font-mono text-xs text-mist">
        no alerts yet
      </div>
    );
  }

  return (
    <div className="relative h-48">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={52}
            outerRadius={76}
            paddingAngle={2}
            strokeWidth={0}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={SEVERITY_COLOR[entry.name as Severity]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "#171F2A",
              border: "1px solid #1E2733",
              borderRadius: 6,
              fontSize: 12,
              fontFamily: "var(--font-plex-mono)",
            }}
            labelStyle={{ color: "#E8EDF2" }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-2xl text-paper">{total}</span>
        <span className="text-[11px] text-mist">total</span>
      </div>
    </div>
  );
}
