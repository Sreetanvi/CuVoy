import {
  AI_DISCLAIMER,
  COST_LABEL_UI,
  CostAmountSchema,
  PlanRequestSchema,
  PlanResultSchema,
  WeatherSchema,
} from "@cuvoy/contracts";
import { describe, expect, it } from "vitest";

describe("shared Zod contracts", () => {
  it("accepts a valid plan request and rejects missing dates", () => {
    const ok = PlanRequestSchema.safeParse({
      user_prompt: "3 days in Bengaluru for museums",
      location: { query: "Bengaluru" },
      travel_dates: { duration_days: 3 },
    });
    expect(ok.success).toBe(true);

    const missing = PlanRequestSchema.safeParse({
      user_prompt: "weekend trip",
      location: { query: "Paris" },
      travel_dates: {},
    });
    expect(missing.success).toBe(false);
  });

  it("enforces three-tier cost labels", () => {
    expect(COST_LABEL_UI.verified_fare).toBe("Verified");
    expect(COST_LABEL_UI.estimated_cost).toBe("Estimated");
    expect(COST_LABEL_UI.unavailable).toBe("Unavailable");
    expect(CostAmountSchema.safeParse({ amount: null, currency: "INR", label: "unavailable" }).success).toBe(
      true,
    );
    expect(
      CostAmountSchema.safeParse({ amount: 10, currency: "INR", label: "unavailable" }).success,
    ).toBe(false);
    expect(
      CostAmountSchema.safeParse({ amount: null, currency: "INR", label: "estimated_cost" }).success,
    ).toBe(false);
  });

  it("keeps historical climate from being labeled a live forecast", () => {
    expect(
      WeatherSchema.safeParse({
        source: "historical_climate",
        is_forecast: false,
        confidence: "moderate",
      }).success,
    ).toBe(true);
    expect(
      WeatherSchema.safeParse({
        source: "historical_climate",
        is_forecast: true,
        confidence: "moderate",
      }).success,
    ).toBe(false);
  });

  it("parses a minimal itinerary result in destination-local time", () => {
    const parsed = PlanResultSchema.safeParse({
      plan_id: "plan-1",
      timezone: "Asia/Kolkata",
      preferences: { interests: ["history"], pace: "moderate" },
      itinerary: {
        timezone: "Asia/Kolkata",
        currency: "INR",
        narrative: "A museum morning.",
        days: [
          {
            day_index: 0,
            date: "2026-04-10",
            timezone: "Asia/Kolkata",
            city: "Bengaluru",
            items: [
              {
                type: "activity",
                start: { timezone: "Asia/Kolkata", local_time: "2026-04-10T09:00:00" },
                end: { timezone: "Asia/Kolkata", local_time: "2026-04-10T11:00:00" },
                title: "City Museum",
                place: {
                  id: "p1",
                  name: "City Museum",
                  lat: 12.97,
                  lng: 77.59,
                  category: "museum",
                  source: "osm",
                },
                warnings: [],
                locked: false,
              },
            ],
          },
        ],
      },
      map: {
        markers: [{ place_id: "p1", lat: 12.97, lng: 77.59, label: "City Museum", day_index: 0 }],
      },
      routes: [],
      provenance: [],
      validation: { valid: true, issues: [] },
    });
    expect(parsed.success).toBe(true);
    expect(AI_DISCLAIMER).toContain("Please verify important details before travel.");
  });
});
