"use client";

import type { ItineraryItem } from "@cuvoy/contracts";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { usePlanSession } from "@/context/PlanSessionContext";
import { clockFromLocal } from "@/lib/format";

export function MealBlock({ item, dayIndex }: { item: ItineraryItem; dayIndex: number }) {
  const { regenerate, phase, readOnly } = usePlanSession();
  const [start, setStart] = useState(clockFromLocal(item.start));
  const [end, setEnd] = useState(clockFromLocal(item.end));
  const busy = phase === "submitting" || phase === "running";

  return (
    <article className="rounded-md border border-dashed border-border bg-muted/40 px-3 py-2">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">Meal</p>
      <p className="text-sm font-medium">{item.title ?? "Meal"}</p>
      {readOnly ? (
        <p className="mt-1 text-xs text-muted-foreground">
          {clockFromLocal(item.start)}–{clockFromLocal(item.end)}
        </p>
      ) : (
      <div className="mt-2 flex flex-wrap items-end gap-2">
        <label className="text-xs text-muted-foreground">
          Start
          <input
            type="time"
            className="mt-1 block h-8 rounded-md border border-border bg-background px-2 text-sm"
            value={start}
            onChange={(event) => setStart(event.target.value)}
          />
        </label>
        <label className="text-xs text-muted-foreground">
          End
          <input
            type="time"
            className="mt-1 block h-8 rounded-md border border-border bg-background px-2 text-sm"
            value={end}
            onChange={(event) => setEnd(event.target.value)}
          />
        </label>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={() =>
            void regenerate({
              meal_override: {
                day_index: dayIndex,
                meal: item.title ?? "meal",
                start_local: start,
                end_local: end,
                skip: false,
              },
            })
          }
        >
          Update meal
        </Button>
      </div>
      )}
    </article>
  );
}
