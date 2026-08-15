"use client";

import { ICS_FILENAME, WARM_GENERATION_TIMEOUT_MS } from "@cuvoy/contracts";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { usePlanSession } from "@/context/PlanSessionContext";
import { downloadIcs } from "@/lib/exportApi";

export function IcsDownload() {
  const { planId, result } = usePlanSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!planId) {
    return null;
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        type="button"
        size="sm"
        variant="outline"
        data-testid="ics-download"
        disabled={busy}
        onClick={() => {
          setBusy(true);
          setError(null);
          void downloadIcs(planId, WARM_GENERATION_TIMEOUT_MS, result?.itinerary)
            .catch(() => setError("Could not download the calendar file."))
            .finally(() => setBusy(false));
        }}
      >
        {busy ? "Preparing…" : `Download ${ICS_FILENAME}`}
      </Button>
      {error ? <p className="text-[11px] text-accent-brown">{error}</p> : null}
    </div>
  );
}
