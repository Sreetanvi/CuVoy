"use client";

import { IcsDownload } from "@/components/export/IcsDownload";
import { PdfExport } from "@/components/export/PdfExport";
import { MealBlock } from "@/components/planner/MealBlock";
import { StopCard } from "@/components/planner/StopCard";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { usePlanSession } from "@/context/PlanSessionContext";
import { useTripControls } from "@/context/TripControlsContext";
import { exclusionDisplayName } from "@/lib/exclusionLabel";
import { formatCost } from "@/lib/format";
import { sequenceByPlaceId, visitStopsForDays } from "@/lib/mapStops";

export function ItineraryPanel() {
  const { result, selectedDayIndex, setSelectedDayIndex, phase, regenerate, readOnly, showFullTrip } =
    usePlanSession();
  const { openAuth } = useAuth();
  const { controls } = useTripControls();

  if (!result) {
    return (
      <div className="flex h-full min-h-[220px] w-full flex-col">
        <div className="border-b border-border px-4 py-2 text-xs uppercase tracking-wide text-muted-foreground">
          Itinerary
        </div>
        <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
          {phase === "running" || phase === "submitting"
            ? "Building your day-by-day timeline…"
            : "Day-by-day stops, meals, costs, and crowd confidence will land in this panel."}
        </div>
      </div>
    );
  }

  const day = result.itinerary.days.find((entry) => entry.day_index === selectedDayIndex) ?? result.itinerary.days[0];
  const sequenceForPlace = sequenceByPlaceId(
    visitStopsForDays(showFullTrip ? result.itinerary.days : day ? [day] : [], {
      continuous: showFullTrip,
    }),
  );
  const transport = day?.daily_cost?.transport;
  const showTransport = controls.show_transport_cost && Boolean(day?.daily_cost?.transport_shown);

  return (
    <div className="flex h-full min-h-[220px] w-full flex-col" data-testid="itinerary-panel">
      <div className="border-b border-border px-4 py-2">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Itinerary</p>
          <div className="flex flex-wrap justify-end gap-1">
            <IcsDownload />
            {readOnly ? null : <PdfExport />}
            {readOnly ? null : (
              <>
                <Button type="button" size="sm" variant="outline" onClick={() => openAuth("save")}>
                  Save
                </Button>
                <Button type="button" size="sm" onClick={() => openAuth("share")}>
                  Share
                </Button>
              </>
            )}
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {result.itinerary.days.map((entry) => (
            <button
              key={entry.day_index}
              type="button"
              className={`rounded-md px-2 py-1 text-xs ${entry.day_index === day?.day_index ? "bg-muted font-medium" : "text-muted-foreground"}`}
              onClick={() => setSelectedDayIndex(entry.day_index)}
            >
              Day {entry.day_index + 1}
            </button>
          ))}
        </div>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {result.itinerary.narrative ? (
          <p className="text-sm text-muted-foreground">{result.itinerary.narrative}</p>
        ) : null}
        {day?.weather ? (
          <p className="text-xs text-muted-foreground">
            {day.weather.summary ?? (day.weather.is_forecast ? "Forecast" : "Typical climate")}
            {day.weather.is_forecast ? "" : " (not a live forecast)"}
          </p>
        ) : null}
        {day?.items.map((item, index) => {
          if (item.type === "meal") {
            return <MealBlock key={`${day.day_index}-meal-${index}`} item={item} dayIndex={day.day_index} />;
          }
          return (
            <StopCard
              key={`${day.day_index}-${index}`}
              item={item}
              sequence={item.place ? sequenceForPlace.get(item.place.id) : undefined}
            />
          );
        })}
        {result.explainability?.exclusions?.length ? (
          <details className="rounded-md border border-border px-3 py-2">
            <summary className="cursor-pointer text-xs font-medium">
              Why some places were skipped ({result.explainability.exclusions.length})
            </summary>
            <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
              {result.explainability.exclusions.map((exclusion, index) => (
                <li key={`${exclusion.place_id ?? "place"}-${index}`}>
                  {exclusionDisplayName(exclusion, result)}: {exclusion.reason}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
        {result.alternatives?.swap_suggestions?.length ? (
          <div>
            <p className="text-xs font-medium">Swap suggestions</p>
            <ul className="mt-1 space-y-2">
              {result.alternatives.swap_suggestions.map((suggestion) => (
                <li key={suggestion.place_id} className="flex items-center justify-between gap-2 text-xs">
                  <span>
                    {suggestion.name} — {suggestion.reason}
                  </span>
                  {suggestion.swap_for_place_id && !readOnly ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        void regenerate({
                          swap: {
                            from_place_id: suggestion.swap_for_place_id!,
                            to_place_id: suggestion.place_id,
                          },
                        })
                      }
                    >
                      Swap
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {day?.daily_cost ? (
          <p className="text-xs text-muted-foreground">
            Day total{" "}
            {formatCost({
              amount: showTransport
                ? day.daily_cost.total_including_transport
                : day.daily_cost.total_excluding_transport,
              currency: day.daily_cost.currency,
            }) || "Unavailable"}
            {showTransport && transport ? ` · transport ${formatCost(transport)}` : ""}
          </p>
        ) : null}
      </div>
    </div>
  );
}
