"use client";

import type { OwnedVehicle, PublicTransportMode } from "@cuvoy/contracts";
import { MAX_TRANSIT_MINUTES } from "@cuvoy/contracts";
import { ChevronDown, ChevronUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { usePlanSession } from "@/context/PlanSessionContext";
import { useTripControls } from "@/context/TripControlsContext";

const VEHICLES: OwnedVehicle[] = ["car", "bike", "camper", "bicycle"];
const PUBLIC_MODES: PublicTransportMode[] = ["mixed", "walking", "metro", "taxi", "bus"];

export function TripControls() {
  const { controls, patchControls, collapsed, setCollapsed } = useTripControls();
  const { planId, regenerate, phase } = usePlanSession();
  const busy = phase === "submitting" || phase === "running";
  const owns = controls.transportation?.owns_vehicle ?? false;

  return (
    <section className="border-t border-border bg-card">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-2 text-left text-sm font-medium"
        onClick={() => setCollapsed(!collapsed)}
        aria-expanded={!collapsed}
      >
        Trip Controls
        {collapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
      </button>
      {collapsed ? null : (
        <div className="grid gap-3 px-4 pb-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Max transit
            <select
              className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
              value={controls.max_transit_preset}
              onChange={(event) =>
                patchControls({
                  max_transit_preset: event.target.value as typeof controls.max_transit_preset,
                })
              }
            >
              {(Object.keys(MAX_TRANSIT_MINUTES) as Array<typeof controls.max_transit_preset>).map(
                (preset) => (
                  <option key={preset} value={preset}>
                    {preset.replaceAll("_", " ")}
                  </option>
                ),
              )}
            </select>
          </label>
          {controls.max_transit_preset === "custom" ? (
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Max minutes
              <input
                type="number"
                min={1}
                className="h-9 rounded-md border border-border bg-background px-2 text-sm"
                value={controls.max_transit_minutes ?? 40}
                onChange={(event) =>
                  patchControls({ max_transit_minutes: Number(event.target.value) })
                }
              />
            </label>
          ) : null}
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Pace
            <select
              className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
              value={controls.pace}
              onChange={(event) =>
                patchControls({ pace: event.target.value as typeof controls.pace })
              }
            >
              <option value="relaxed">relaxed</option>
              <option value="moderate">moderate</option>
              <option value="packed">packed</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Day start
            <input
              type="time"
              className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
              value={controls.day_start_local}
              onChange={(event) => patchControls({ day_start_local: event.target.value })}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Day end
            <input
              type="time"
              className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
              value={controls.day_end_local}
              onChange={(event) => patchControls({ day_end_local: event.target.value })}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Lunch
            <span className="flex gap-1">
              <input
                type="time"
                className="h-9 flex-1 rounded-md border border-border bg-background px-2 text-sm"
                value={controls.lunch.start_local}
                onChange={(event) =>
                  patchControls({ lunch: { ...controls.lunch, start_local: event.target.value } })
                }
              />
              <input
                type="time"
                className="h-9 flex-1 rounded-md border border-border bg-background px-2 text-sm"
                value={controls.lunch.end_local}
                onChange={(event) =>
                  patchControls({ lunch: { ...controls.lunch, end_local: event.target.value } })
                }
              />
            </span>
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Dinner
            <span className="flex gap-1">
              <input
                type="time"
                className="h-9 flex-1 rounded-md border border-border bg-background px-2 text-sm"
                value={controls.dinner.start_local}
                onChange={(event) =>
                  patchControls({ dinner: { ...controls.dinner, start_local: event.target.value } })
                }
              />
              <input
                type="time"
                className="h-9 flex-1 rounded-md border border-border bg-background px-2 text-sm"
                value={controls.dinner.end_local}
                onChange={(event) =>
                  patchControls({ dinner: { ...controls.dinner, end_local: event.target.value } })
                }
              />
            </span>
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted-foreground">
            Transport
            <select
              className="h-9 rounded-md border border-border bg-background px-2 text-sm"
              value={owns ? `own:${controls.transportation?.vehicle ?? "car"}` : `pub:${controls.transportation?.public_mode ?? "mixed"}`}
              onChange={(event) => {
                const value = event.target.value;
                if (value.startsWith("own:")) {
                  patchControls({
                    transportation: {
                      owns_vehicle: true,
                      vehicle: value.slice(4) as OwnedVehicle,
                      public_mode: null,
                    },
                  });
                } else {
                  patchControls({
                    transportation: {
                      owns_vehicle: false,
                      vehicle: null,
                      public_mode: value.slice(4) as PublicTransportMode,
                    },
                  });
                }
              }}
            >
              {VEHICLES.map((option) => (
                <option key={option} value={`own:${option}`}>
                  {option}
                </option>
              ))}
              {PUBLIC_MODES.map((option) => (
                <option key={option} value={`pub:${option}`}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={controls.show_transport_cost}
              onChange={(event) => patchControls({ show_transport_cost: event.target.checked })}
            />
            Show estimated transport cost
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={controls.hidden_gems}
              onChange={(event) => patchControls({ hidden_gems: event.target.checked })}
            />
            Hidden gems
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={controls.group.enabled}
              onChange={(event) =>
                patchControls({ group: { ...controls.group, enabled: event.target.checked } })
              }
            />
            Group planning
          </label>
          {controls.group.enabled ? (
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Priority
              <select
                className="h-9 rounded-md border border-border bg-background px-2 text-sm"
                value={controls.group.priority}
                onChange={(event) =>
                  patchControls({
                    group: {
                      ...controls.group,
                      priority: event.target.value as typeof controls.group.priority,
                    },
                  })
                }
              >
                <option value="everyone">everyone</option>
                <option value="team_lead">team lead</option>
              </select>
            </label>
          ) : null}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={controls.accessibility.kids}
              onChange={(event) =>
                patchControls({
                  accessibility: { ...controls.accessibility, kids: event.target.checked },
                })
              }
            />
            Kids
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={controls.accessibility.elderly}
              onChange={(event) =>
                patchControls({
                  accessibility: { ...controls.accessibility, elderly: event.target.checked },
                })
              }
            />
            Elderly
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={controls.accessibility.wheelchair}
              onChange={(event) =>
                patchControls({
                  accessibility: { ...controls.accessibility, wheelchair: event.target.checked },
                })
              }
            />
            Wheelchair
          </label>
          <div className="flex items-end">
            <Button
              type="button"
              size="sm"
              data-testid="apply-trip-controls"
              disabled={!planId || busy}
              onClick={() => void regenerate({ trip_controls: controls })}
            >
              Apply
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
