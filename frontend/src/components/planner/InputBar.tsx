"use client";

import type { OwnedVehicle, PublicTransportMode } from "@cuvoy/contracts";
import { PlanRequestSchema } from "@cuvoy/contracts";
import { useState } from "react";

import { AutosizeTextarea } from "@/components/ui/autosize-textarea";
import { Button } from "@/components/ui/button";
import { usePlanSession } from "@/context/PlanSessionContext";
import { useTripControls } from "@/context/TripControlsContext";
import { resolveLocationQuery } from "@/lib/destination";

const VEHICLES: OwnedVehicle[] = ["car", "bike", "camper", "bicycle"];
const PUBLIC_MODES: PublicTransportMode[] = ["mixed", "walking", "metro", "taxi", "bus"];

export function InputBar() {
  const { generate, phase } = usePlanSession();
  const { controls } = useTripControls();
  const [prompt, setPrompt] = useState("");
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [durationDays, setDurationDays] = useState("4");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [ownsVehicle, setOwnsVehicle] = useState<"yes" | "no" | "">("");
  const [vehicle, setVehicle] = useState<OwnedVehicle>("car");
  const [publicMode, setPublicMode] = useState<PublicTransportMode>("mixed");
  const [formError, setFormError] = useState<string | null>(null);
  const busy = phase === "submitting" || phase === "running";

  return (
    <form
      className="flex flex-col gap-2 border-t border-border bg-background p-3"
      onSubmit={(event) => {
        event.preventDefault();
        setFormError(null);
        const travel_dates =
          startDate && endDate
            ? { start_date: startDate, end_date: endDate, duration_days: null }
            : { start_date: null, end_date: null, duration_days: Number(durationDays) || 4 };
        const transportation =
          ownsVehicle === ""
            ? null
            : ownsVehicle === "yes"
              ? { owns_vehicle: true as const, vehicle, public_mode: null }
              : { owns_vehicle: false as const, vehicle: null, public_mode: publicMode };
        const locationQuery = resolveLocationQuery(destination, prompt);
        if (!locationQuery) {
          setFormError("Add a destination (city, region, or country) so we can place the trip.");
          return;
        }
        const parsed = PlanRequestSchema.safeParse({
          user_prompt: prompt.trim(),
          location: { query: locationQuery },
          travel_dates,
          budget: budgetAmount
            ? { daily_amount: Number(budgetAmount), currency, raw: `${currency} ${budgetAmount}/day` }
            : null,
          transportation,
          trip_controls: controls,
        });
        if (!parsed.success) {
          setFormError(parsed.error.issues[0]?.message ?? "Check your trip request and dates.");
          return;
        }
        void generate(parsed.data);
      }}
    >
      <div className="grid gap-2 lg:grid-cols-[minmax(0,1.4fr)_minmax(12rem,0.7fr)_minmax(0,1fr)_auto]">
        <label className="min-w-0 text-xs text-muted-foreground">
          Trip request
          <AutosizeTextarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            minRows={2}
            maxRows={10}
            required
            placeholder="2 weeks in Rajasthan, forts and food…"
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
          />
        </label>
        <label className="min-w-0 text-xs text-muted-foreground">
          Destination
          <input
            value={destination}
            onChange={(event) => setDestination(event.target.value)}
            placeholder="Rajasthan, India"
            autoComplete="address-level2"
            className="mt-1 h-11 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground"
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs text-muted-foreground">
            Daily budget
            <span className="mt-1 flex gap-1">
              <input
                value={currency}
                onChange={(event) => setCurrency(event.target.value.toUpperCase())}
                className="h-9 w-16 rounded-md border border-border bg-background px-2 text-sm"
              />
              <input
                type="number"
                min={1}
                value={budgetAmount}
                onChange={(event) => setBudgetAmount(event.target.value)}
                placeholder="5000"
                className="h-9 min-w-0 flex-1 rounded-md border border-border bg-background px-2 text-sm"
              />
            </span>
          </label>
          <label className="text-xs text-muted-foreground">
            Start
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 text-sm"
            />
          </label>
          <label className="text-xs text-muted-foreground">
            End
            <input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 text-sm"
            />
          </label>
        </div>
        <div className="flex flex-col justify-end gap-2">
          <label className="text-xs text-muted-foreground">
            Duration (if no dates)
            <input
              type="number"
              min={1}
              value={durationDays}
              onChange={(event) => setDurationDays(event.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 text-sm"
            />
          </label>
          <Button type="submit" size="lg" disabled={busy} data-testid="generate-plan">
            {busy ? "Planning…" : "Generate"}
          </Button>
        </div>
      </div>
      <fieldset className="flex flex-wrap items-center gap-3 text-xs">
        <legend className="sr-only">Do you have your own vehicle?</legend>
        <span className="text-muted-foreground">Own vehicle?</span>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="owns-vehicle"
            checked={ownsVehicle === "yes"}
            onChange={() => setOwnsVehicle("yes")}
          />
          Yes
        </label>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="owns-vehicle"
            checked={ownsVehicle === "no"}
            onChange={() => setOwnsVehicle("no")}
          />
          No
        </label>
        {ownsVehicle === "yes" ? (
          <select
            className="h-8 rounded-md border border-border bg-background px-2"
            value={vehicle}
            onChange={(event) => setVehicle(event.target.value as OwnedVehicle)}
          >
            {VEHICLES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        ) : null}
        {ownsVehicle === "no" ? (
          <select
            className="h-8 rounded-md border border-border bg-background px-2"
            value={publicMode}
            onChange={(event) => setPublicMode(event.target.value as PublicTransportMode)}
          >
            {PUBLIC_MODES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        ) : null}
      </fieldset>
      {formError ? <p className="text-xs text-accent-brown">{formError}</p> : null}
    </form>
  );
}
