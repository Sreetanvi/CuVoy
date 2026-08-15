"use client";

import type { CrowdConfidence } from "@cuvoy/contracts";

import { cn } from "@/lib/utils";

const LEVEL: Record<CrowdConfidence["level"], string> = {
  very_quiet: "Very quiet",
  quiet: "Quiet",
  moderate: "Moderate",
  busy: "Busy",
  very_busy: "Very busy",
};

export function CrowdBadge({ crowd }: { crowd: CrowdConfidence }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm border border-border px-1.5 py-0.5 text-[11px]",
      )}
      title={crowd.reasons.join(" · ")}
    >
      {LEVEL[crowd.level]}
      <span className="text-muted-foreground">({crowd.confidence})</span>
    </span>
  );
}
