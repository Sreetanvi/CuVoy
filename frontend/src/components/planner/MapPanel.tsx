"use client";

import dynamic from "next/dynamic";

import { usePlanSession } from "@/context/PlanSessionContext";

const MapCanvas = dynamic(
  () => import("@/components/planner/MapCanvas").then((mod) => mod.MapCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
        Loading map…
      </div>
    ),
  },
);

export function MapPanel({ visible = true }: { visible?: boolean }) {
  const { result, showFullTrip, setShowFullTrip, phase } = usePlanSession();

  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-muted/40">
      <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-2">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">Map</p>
        {result ? (
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={showFullTrip}
              onChange={(event) => setShowFullTrip(event.target.checked)}
            />
            Full trip
          </label>
        ) : null}
      </div>
      <div className="relative min-h-0 w-full flex-1">
        <div className="absolute inset-0 h-full w-full">
          <MapCanvas visible={visible} />
        </div>
        {!result ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-muted-foreground">
            {phase === "running" || phase === "submitting"
              ? "Routes appear when the plan is ready."
              : "Stops, route lines, and travel times appear here after you generate a plan."}
          </div>
        ) : null}
      </div>
    </div>
  );
}
