"use client";

import type { ItineraryItem } from "@cuvoy/contracts";

import { CostLabel } from "@/components/planner/CostLabel";
import { CrowdBadge } from "@/components/planner/CrowdBadge";
import { Warnings } from "@/components/planner/Warnings";
import { usePlanSession } from "@/context/PlanSessionContext";
import { useTripControls } from "@/context/TripControlsContext";
import { clockFromLocal, formatCost, formatMinutes } from "@/lib/format";
import { Button } from "@/components/ui/button";

export function StopCard({ item, sequence }: { item: ItineraryItem; sequence?: number }) {
  const {
    selectedPlaceId,
    setSelectedPlaceId,
    lockedStopIds,
    skipStopIds,
    toggleLock,
    toggleSkip,
    regenerate,
    phase,
    readOnly,
  } = usePlanSession();
  const { controls } = useTripControls();
  const place = item.place;
  const selected = place != null && selectedPlaceId === place.id;
  const locked = place != null && lockedStopIds.includes(place.id);
  const skipped = place != null && skipStopIds.includes(place.id);
  const showTransport = controls.show_transport_cost;
  const cost =
    item.cost && (item.cost.label === "unavailable" || item.cost.amount != null)
      ? item.cost
      : null;
  const hideTransportCost = item.type === "transit" && !showTransport;
  const busy = phase === "submitting" || phase === "running";

  return (
    <article
      className={`rounded-md border px-3 py-2 ${selected ? "border-accent-green" : "border-border"} ${skipped ? "opacity-50" : ""}`}
    >
      <button
        type="button"
        className="w-full text-left"
        onClick={() => setSelectedPlaceId(place?.id ?? null)}
      >
        <div className="flex items-baseline justify-between gap-2">
          <p className="text-sm font-medium">
            {sequence != null ? `${sequence}. ` : ""}
            {item.title ?? place?.name ?? item.type}
          </p>
          <p className="shrink-0 text-xs text-muted-foreground">
            {clockFromLocal(item.start)}–{clockFromLocal(item.end)}
          </p>
        </div>
        {item.travel_minutes_buffered != null && item.type === "transit" ? (
          <p className="text-xs text-muted-foreground">
            Travel {formatMinutes(item.travel_minutes_buffered)}
          </p>
        ) : null}
        {item.reason ? <p className="mt-1 text-xs text-muted-foreground">{item.reason}</p> : null}
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {cost && !hideTransportCost ? (
            <>
              <span className="text-xs">{formatCost(cost)}</span>
              <CostLabel kind={cost.label} />
            </>
          ) : null}
          {item.crowd ? <CrowdBadge crowd={item.crowd} /> : null}
        </div>
        {place?.opening_hours ? (
          <p className="mt-1 text-xs text-muted-foreground">Hours: {place.opening_hours}</p>
        ) : null}
        <Warnings codes={item.warnings} />
        {item.reservation?.likely_needed ? (
          <p className="mt-1 text-xs text-accent-brown">{item.reservation.guidance}</p>
        ) : null}
      </button>
      {place && !readOnly ? (
        <div className="mt-2 flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant={locked ? "default" : "outline"}
            disabled={busy}
            onClick={() => toggleLock(place.id)}
          >
            {locked ? "Locked" : "Lock stop"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => {
              toggleSkip(place.id);
              void regenerate({
                skip_stop_ids: skipped
                  ? skipStopIds.filter((id) => id !== place.id)
                  : [...skipStopIds, place.id],
              });
            }}
          >
            {skipped ? "Keep stop" : "Skip"}
          </Button>
        </div>
      ) : null}
    </article>
  );
}
