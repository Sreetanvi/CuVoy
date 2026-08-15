"use client";

import { Button } from "@/components/ui/button";
import { useColdStartContext } from "@/context/ColdStartContext";

export function ColdStartBanner() {
  const { waking, failed, message, retry } = useColdStartContext();

  if (!waking && !failed) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-between gap-4 border-b border-border bg-muted px-4 py-2.5"
    >
      <div className="flex items-center gap-3">
        <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-accent-green animate-cuvoy-pulse" />
        <p className="text-sm">
          {failed
            ? "The planner did not wake. Try again — the second attempt is usually fast."
            : message}
        </p>
      </div>
      {failed ? (
        <Button type="button" size="sm" variant="outline" onClick={() => void retry()}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
