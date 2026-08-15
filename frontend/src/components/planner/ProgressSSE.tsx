"use client";

import { usePlanSession } from "@/context/PlanSessionContext";

export function ProgressSSE() {
  const { phase, progress, stageMessage, errorMessage, recoverable, creditRefunded } =
    usePlanSession();

  if (phase !== "submitting" && phase !== "running" && phase !== "error") {
    return null;
  }

  if (phase === "error" && errorMessage) {
    return (
      <div className="border-b border-border bg-muted px-4 py-2 text-sm" role="alert">
        <p>{errorMessage}</p>
        {creditRefunded ? (
          <p className="text-xs text-muted-foreground">Your plan credit was returned.</p>
        ) : null}
        {recoverable ? (
          <p className="text-xs text-muted-foreground">You can try generating again.</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="border-b border-border bg-muted px-4 py-2" role="status" aria-live="polite">
      <div className="flex items-center justify-between gap-3 text-sm">
        <p>{stageMessage}</p>
        <span className="tabular-nums text-xs text-muted-foreground">{progress}%</span>
      </div>
      <div className="mt-2 h-1.5 w-full rounded-sm bg-background">
        <div
          className="h-1.5 rounded-sm bg-accent-green"
          style={{ width: `${Math.min(100, Math.max(progress, 4))}%` }}
        />
      </div>
    </div>
  );
}
