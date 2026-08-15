"use client";

import { WARM_GENERATION_TIMEOUT_MS } from "@cuvoy/contracts";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { usePlanSession } from "@/context/PlanSessionContext";
import { downloadPdf } from "@/lib/exportApi";

export function PdfExport() {
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
        data-testid="pdf-export"
        disabled={busy}
        onClick={() => {
          setBusy(true);
          setError(null);
          void downloadPdf(planId, WARM_GENERATION_TIMEOUT_MS, result)
            .catch(() => setError("Could not prepare the PDF."))
            .finally(() => setBusy(false));
        }}
      >
        {busy ? "Preparing…" : "Download PDF"}
      </Button>
      {error ? <p className="text-[11px] text-accent-brown">{error}</p> : null}
    </div>
  );
}
