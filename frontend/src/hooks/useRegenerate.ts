"use client";

import { usePlanSession } from "@/context/PlanSessionContext";

export function useRegenerate() {
  const { regenerate, phase, planId } = usePlanSession();
  return {
    regenerate,
    busy: phase === "submitting" || phase === "running",
    enabled: Boolean(planId),
  };
}
