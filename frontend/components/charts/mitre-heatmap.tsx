"use client";

import { useMemo, useState } from "react";
import type { MitreHeatmapEntry, MitreTechnique } from "@/lib/types";
import { cn } from "@/lib/utils";

const TACTIC_ORDER = [
  "reconnaissance",
  "resource-development",
  "initial-access",
  "execution",
  "persistence",
  "privilege-escalation",
  "defense-evasion",
  "credential-access",
  "discovery",
  "lateral-movement",
  "collection",
  "command-and-control",
  "exfiltration",
  "impact",
];

const TACTIC_LABEL: Record<string, string> = {
  reconnaissance: "Recon",
  "resource-development": "Resource Dev",
  "initial-access": "Initial Access",
  execution: "Execution",
  persistence: "Persistence",
  "privilege-escalation": "Priv Esc",
  "defense-evasion": "Defense Evasion",
  "credential-access": "Cred Access",
  discovery: "Discovery",
  "lateral-movement": "Lateral Move",
  collection: "Collection",
  "command-and-control": "C2",
  exfiltration: "Exfil",
  impact: "Impact",
};

function heatColor(count: number, max: number): string {
  if (count === 0) return "bg-surface-raised border border-line";
  const intensity = max > 0 ? count / max : 0;
  if (intensity > 0.66) return "bg-threat border border-threat";
  if (intensity > 0.33) return "bg-amber border border-amber";
  return "bg-cyan/70 border border-cyan";
}

export function MitreHeatmap({
  techniques,
  heatmap,
}: {
  techniques: MitreTechnique[];
  heatmap: MitreHeatmapEntry[];
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  const countByTechnique = useMemo(() => {
    const map = new Map<string, number>();
    for (const entry of heatmap) map.set(entry.technique_id, entry.alert_count);
    return map;
  }, [heatmap]);

  const maxCount = useMemo(
    () => Math.max(1, ...heatmap.map((entry) => entry.alert_count)),
    [heatmap],
  );

  const columns = useMemo(() => {
    const byTactic = new Map<string, MitreTechnique[]>();
    for (const tactic of TACTIC_ORDER) byTactic.set(tactic, []);
    for (const technique of techniques) {
      const list = byTactic.get(technique.tactic);
      if (list) list.push(technique);
    }
    return Array.from(byTactic.entries()).filter(([, list]) => list.length > 0);
  }, [techniques]);

  const hoveredTechnique = techniques.find((t) => t.id === hovered);

  return (
    <div>
      <div className="flex gap-1.5 overflow-x-auto pb-2">
        {columns.map(([tactic, list]) => (
          <div key={tactic} className="flex w-20 shrink-0 flex-col gap-1">
            <div className="mb-1 h-8 font-mono text-[10px] uppercase leading-tight text-mist">
              {TACTIC_LABEL[tactic] ?? tactic}
            </div>
            {list.map((technique) => {
              const count = countByTechnique.get(technique.id) ?? 0;
              return (
                <button
                  key={technique.id}
                  onMouseEnter={() => setHovered(technique.id)}
                  onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(technique.id)}
                  onBlur={() => setHovered(null)}
                  className={cn(
                    "h-5 rounded-sm transition-transform hover:scale-[1.15]",
                    heatColor(count, maxCount),
                  )}
                  aria-label={`${technique.name}: ${count} alerts`}
                />
              );
            })}
          </div>
        ))}
      </div>

      <div className="mt-3 flex h-8 items-center gap-2 border-t border-line pt-3 font-mono text-[11px] text-mist">
        {hoveredTechnique ? (
          <>
            <span className="text-paper">{hoveredTechnique.id}</span>
            <span>{hoveredTechnique.name}</span>
            <span className="text-mist">·</span>
            <span>{countByTechnique.get(hoveredTechnique.id) ?? 0} alerts</span>
          </>
        ) : (
          <span>hover a technique for detail</span>
        )}
      </div>
    </div>
  );
}
