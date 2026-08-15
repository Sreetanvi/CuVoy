import type { MaxTransitPreset, TransportMode } from "./enums";

export const PLAN_CREDITS_PER_DAY = 3;
export const BUDGET_LLM_CALLS = 6;
export const BUDGET_MAPBOX_SEARCH = 20;
export const BUDGET_MAPBOX_MATRIX = 3;
export const BUDGET_OSM = 6;
export const BUDGET_WEATHER = 1;
export const BUDGET_VERIFICATION = 5;
export const REGEN_BUDGET_FRACTION = 0.4;
export const MAX_CACHE_PAYLOAD_BYTES = 250_000;

export const TTL_PLACES = 30 * 86400;
export const TTL_GEOCODING = 90 * 86400;
export const TTL_MATRIX = 24 * 3600;
export const TTL_DIRECTIONS = 3 * 3600;
export const TTL_WEATHER_FORECAST = 20 * 60;
export const TTL_WEATHER_CLIMATE = 30 * 86400;
export const TTL_GTFS = 30 * 86400;
export const TTL_AI_ITINERARY = 7 * 86400;
export const TTL_HOLIDAYS = 30 * 86400;
export const TTL_OSM_POI = 30 * 86400;
export const TTL_CREDITS = 24 * 3600;
export const TTL_IDEMPOTENCY = 24 * 3600;
export const TTL_CHECKPOINT = 24 * 3600;
export const TTL_SESSION = 6 * 3600;
export const OR_TOOLS_TIMEOUT_SECONDS = 10;
export const OR_TOOLS_MAX_STOPS_PER_DAY = 20;
export const COLD_START_CLIENT_TIMEOUT_MS = 90_000;
export const WARM_GENERATION_TIMEOUT_MS = 30_000;
export const COLD_START_UI_MESSAGE = "Waking up the AI planner…";

export const DEFAULT_DAY_START_LOCAL = "09:00";
export const DEFAULT_DAY_END_LOCAL = "21:00";
export const DEFAULT_LUNCH_START = "13:00";
export const DEFAULT_LUNCH_END = "14:00";
export const DEFAULT_DINNER_START = "19:00";
export const DEFAULT_DINNER_END = "21:00";
export const MEAL_MIN_DURATION_MINUTES = 60;

export const DEFAULT_DWELL_MINUTES: Record<string, number> = {
  museum: 120,
  viewpoint: 30,
  restaurant: 90,
};

export const MAX_TRANSIT_MINUTES: Record<MaxTransitPreset, number | null> = {
  walkable: 20,
  relaxed: 30,
  balanced: 40,
  explorer: 60,
  no_limit: null,
  custom: null,
};

export const TRANSIT_BUFFER: Record<TransportMode, number> = {
  walking: 0.08,
  car: 0.1,
  bike: 0.1,
  camper: 0.1,
  bicycle: 0.1,
  taxi: 0.15,
  metro: 0.22,
  bus: 0.22,
  mixed: 0.22,
};

export const API_V1_PREFIX = "/api/v1";
export const PATH_HEALTH = "/health";
export const PATH_PLAN = "/api/v1/plan";
export const PATH_REGENERATE = "/api/v1/plan/{id}/regenerate";
export const PATH_PLAN_GET = "/api/v1/plan/{id}";
export const PATH_PLAN_STATUS = "/api/v1/plan/{id}/status";
export const PATH_EXPORT_PDF = "/api/v1/plan/{id}/export/pdf";
export const PATH_EXPORT_ICS = "/api/v1/plan/{id}/export/ics";
export const PATH_TRIPS = "/api/v1/trips";
export const PATH_TRIPS_GET = "/api/v1/trips/{id}";
export const PATH_TRIPS_SHARED = "/api/v1/trips/shared/{slug}";
export const PATH_ACCOUNT = "/api/v1/account";
export const PUBLIC_ORIGIN = "https://cuvoy.vercel.app";
export const ICS_FILENAME = "cuvoy-trip.ics";

export const COST_LABEL_UI = {
  verified_fare: "Verified",
  estimated_cost: "Estimated",
  unavailable: "Unavailable",
} as const;

export const AI_DISCLAIMER =
  "Travel times, prices, and itineraries are estimates generated using AI and third-party mapping services. Please verify important details before travel.";
