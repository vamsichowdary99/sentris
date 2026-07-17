"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import type { Alert } from "@/lib/types";

function bucketByHour(alerts: Alert[]): { hour: string; count: number }[] {
  const buckets = new Map<number, number>();
  const now = Date.now();

  for (let i = 23; i >= 0; i--) {
    buckets.set(i, 0);
  }

  for (const alert of alerts) {
    const hoursAgo = Math.floor((now - new Date(alert.occurred_at).getTime()) / 3_600_000);
    if (hoursAgo >= 0 && hoursAgo < 24) {
      buckets.set(hoursAgo, (buckets.get(hoursAgo) ?? 0) + 1);
    }
  }

  return Array.from(buckets.entries())
    .sort((a, b) => b[0] - a[0])
    .map(([hoursAgo, count]) => ({ hour: `-${hoursAgo}h`, count }));
}

export function LiveSignal({ alerts }: { alerts: Alert[] }) {
  const data = bucketByHour(alerts);

  return (
    <div className="h-16 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="signalFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4FD1E8" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#4FD1E8" stopOpacity={0} />
            </linearGradient>
          </defs>
          <YAxis hide domain={[0, "dataMax + 1"]} />
          <Tooltip
            contentStyle={{
              background: "#171F2A",
              border: "1px solid #1E2733",
              borderRadius: 6,
              fontSize: 12,
              fontFamily: "var(--font-plex-mono)",
            }}
            labelStyle={{ color: "#8B98A8" }}
            formatter={(value: number) => [`${value} alerts`, ""]}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#4FD1E8"
            strokeWidth={1.5}
            fill="url(#signalFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
