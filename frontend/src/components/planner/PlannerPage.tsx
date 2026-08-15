"use client";

import { WARM_GENERATION_TIMEOUT_MS, type PlanResult } from "@cuvoy/contracts";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { PlanSessionProvider } from "@/context/PlanSessionContext";
import { getOwnedTrip } from "@/lib/tripApi";

export function PlannerPage({
  planId,
  savedTripId,
  initialResult,
  readOnly = false,
  shareTitle,
}: {
  planId?: string;
  savedTripId?: string;
  initialResult?: PlanResult | null;
  readOnly?: boolean;
  shareTitle?: string;
}) {
  const [result, setResult] = useState<PlanResult | null>(initialResult ?? null);
  const [title, setTitle] = useState(shareTitle);
  const [ready, setReady] = useState(!savedTripId || Boolean(initialResult));

  useEffect(() => {
    if (initialResult || !savedTripId) {
      return;
    }
    let cancelled = false;
    void getOwnedTrip(savedTripId, WARM_GENERATION_TIMEOUT_MS)
      .then((owned) => {
        if (cancelled) {
          return;
        }
        setResult(owned.result);
        setTitle(owned.trip.title);
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) {
          setReady(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [initialResult, savedTripId]);

  if (!ready) {
    return (
      <div className="flex h-dvh items-center justify-center text-sm text-muted-foreground">
        Loading saved itinerary…
      </div>
    );
  }

  return (
    <PlanSessionProvider
      initialPlanId={result?.plan_id ?? planId}
      initialResult={result}
      readOnly={readOnly}
    >
      <AppShell readOnly={readOnly} shareTitle={title} />
    </PlanSessionProvider>
  );
}
