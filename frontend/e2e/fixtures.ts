import type { PdfExportResponse, PlanResult } from "@cuvoy/contracts";

export const PLAN_ID = "plan-e2e";

export const planResult: PlanResult = {
  plan_id: PLAN_ID,
  timezone: "Asia/Kolkata",
  preferences: {
    interests: ["history"],
    pace: "moderate",
    food: { dietary_restrictions: [], cuisines: [] },
    hidden_gems: false,
    accessibility: { kids: false, elderly: false, wheelchair: false, notes: null },
    group: { enabled: false, travelers: [], priority: "everyone" },
  },
  itinerary: {
    timezone: "Asia/Kolkata",
    currency: "INR",
    narrative: "A walkable Bengaluru morning.",
    days: [
      {
        day_index: 0,
        date: "2026-04-10",
        timezone: "Asia/Kolkata",
        city: "Bengaluru",
        is_travel_day: false,
        items: [
          {
            type: "activity",
            start: { timezone: "Asia/Kolkata", local_time: "2026-04-10T09:00:00" },
            end: { timezone: "Asia/Kolkata", local_time: "2026-04-10T11:00:00" },
            title: "Bangalore Palace",
            place: {
              id: "p1",
              name: "Bangalore Palace",
              lat: 12.9987,
              lng: 77.5921,
              category: "historic",
              source: "osm",
            },
            cost: { amount: 230, currency: "INR", label: "estimated_cost" },
            locked: false,
            warnings: [],
          },
        ],
      },
    ],
  },
  map: {
    markers: [
      {
        place_id: "p1",
        lat: 12.9987,
        lng: 77.5921,
        label: "Bangalore Palace",
        day_index: 0,
      },
    ],
  },
  routes: [],
  provenance: [],
  validation: { valid: true, issues: [] },
};

export const pdfDocument: PdfExportResponse = {
  plan_id: PLAN_ID,
  renderer: "client",
  title: "Trip to Bengaluru",
  logo_placement: "corner",
  disclaimer:
    "Travel times, prices, and itineraries are estimates generated using AI and third-party mapping services. Please verify important details before travel.",
  timezone: "Asia/Kolkata",
  days: [
    {
      day_index: 0,
      date: "2026-04-10",
      timezone: "Asia/Kolkata",
      timezone_abbrev: "IST",
      city: "Bengaluru",
      stops: [
        {
          start_local: "09:00 IST",
          end_local: "11:00 IST",
          title: "Bangalore Palace",
          notes: null,
          cost: "230 INR (Estimated)",
          cost_label: "Estimated",
        },
      ],
      daily_total: "230 INR",
    },
  ],
  route_labels: [],
  map_hint: "Client map snapshot",
};

export const icsBody = [
  "BEGIN:VCALENDAR",
  "VERSION:2.0",
  "PRODID:-//CuVoy//EN",
  "BEGIN:VEVENT",
  "SUMMARY:Bangalore Palace",
  "DTSTART;TZID=Asia/Kolkata:20260410T090000",
  "DTEND;TZID=Asia/Kolkata:20260410T110000",
  "END:VEVENT",
  "END:VCALENDAR",
].join("\r\n");
