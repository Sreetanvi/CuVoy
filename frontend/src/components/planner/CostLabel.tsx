"use client";

import { COST_LABEL_UI, type CostLabel as CostLabelKind } from "@cuvoy/contracts";

import { cn } from "@/lib/utils";

const styles: Record<CostLabelKind, string> = {
  verified_fare: "border-accent-green text-accent-green",
  estimated_cost: "border-accent-brown text-accent-brown",
  unavailable: "border-muted-foreground text-muted-foreground",
};

export function CostLabel({ kind }: { kind: CostLabelKind }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-sm border px-1.5 py-0.5 text-[11px] font-medium tracking-wide uppercase",
        styles[kind],
      )}
    >
      {COST_LABEL_UI[kind]}
    </span>
  );
}
