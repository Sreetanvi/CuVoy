"""Numeric defaults from PROJECT_SPEC §§5, 16–18. Not user-facing copy."""

from cuvoy_contracts.enums import MaxTransitPreset, TransportMode

# §16 — user-facing plan credits
PLAN_CREDITS_PER_DAY = 3

# §7.3 — per-plan internal API envelope (full plan)
BUDGET_LLM_CALLS = 6
BUDGET_MAPBOX_SEARCH = 20
BUDGET_MAPBOX_MATRIX = 3
BUDGET_OSM = 6
BUDGET_WEATHER = 1
BUDGET_VERIFICATION = 5
REGEN_BUDGET_FRACTION = 0.4

# §31 — skip cache write if normalized payload exceeds this
MAX_CACHE_PAYLOAD_BYTES = 250_000

# §17 — TTLs in seconds
TTL_PLACES = 30 * 86400
TTL_GEOCODING = 90 * 86400
TTL_MATRIX = 24 * 3600
TTL_DIRECTIONS = 3 * 3600
TTL_WEATHER_FORECAST = 20 * 60
TTL_WEATHER_CLIMATE = 30 * 86400
TTL_GTFS = 30 * 86400
TTL_AI_ITINERARY = 7 * 86400
TTL_HOLIDAYS = 30 * 86400
TTL_OSM_POI = 30 * 86400
TTL_CREDITS = 24 * 3600
TTL_IDEMPOTENCY = 24 * 3600
TTL_CHECKPOINT = 24 * 3600
TTL_SESSION = 6 * 3600

# §7.10 / §16 — Render 512 MB discipline
OR_TOOLS_TIMEOUT_SECONDS = 10
OR_TOOLS_MAX_STOPS_PER_DAY = 20

# §18 — Render cold start
COLD_START_CLIENT_TIMEOUT_MS = 90_000
WARM_GENERATION_TIMEOUT_MS = 30_000
COLD_START_UI_MESSAGE = "Waking up the AI planner…"
HIGH_DEMAND_UI_MESSAGE = "CuVoy is handling high demand…"
LLM_MAX_RETRIES = 3
LLM_TIMEOUT_SECONDS = 25.0
LLM_MAX_CONCURRENT = 2

# §29.2 / §33 — external data
FORECAST_HORIZON_DAYS = 16
MAX_MATRIX_COORDINATES = 25
OSM_MATCH_MAX_METERS = 150
WEBSITE_VERIFY_TIMEOUT_SECONDS = 5.0
OVERPASS_TIMEOUT_SECONDS = 30.0

# §5.3
DEFAULT_DAY_START_LOCAL = "09:00"
DEFAULT_DAY_END_LOCAL = "21:00"
DEFAULT_PACE = "moderate"

# §5.5
DEFAULT_LUNCH_START = "13:00"
DEFAULT_LUNCH_END = "14:00"
DEFAULT_DINNER_START = "19:00"
DEFAULT_DINNER_END = "21:00"
MEAL_MIN_DURATION_MINUTES = 60

# §5.4 — minutes
DEFAULT_DWELL_MINUTES: dict[str, int] = {
    "museum": 120,
    "viewpoint": 30,
    "restaurant": 90,
}

# §5.1 — max intra-city transit between consecutive stops (minutes)
MAX_TRANSIT_MINUTES: dict[MaxTransitPreset, int | None] = {
    MaxTransitPreset.WALKABLE: 20,
    MaxTransitPreset.RELAXED: 30,
    MaxTransitPreset.BALANCED: 40,
    MaxTransitPreset.EXPLORER: 60,
    MaxTransitPreset.NO_LIMIT: None,
    MaxTransitPreset.CUSTOM: None,
}

# §5.2 — fraction added on top of Mapbox duration
TRANSIT_BUFFER: dict[TransportMode, float] = {
    TransportMode.WALKING: 0.08,
    TransportMode.CAR: 0.10,
    TransportMode.BIKE: 0.10,
    TransportMode.CAMPER: 0.10,
    TransportMode.BICYCLE: 0.10,
    TransportMode.TAXI: 0.15,
    TransportMode.METRO: 0.22,
    TransportMode.BUS: 0.22,
    TransportMode.MIXED: 0.22,
}

API_V1_PREFIX = "/api/v1"
PATH_HEALTH = "/health"
PATH_PLAN = "/api/v1/plan"
PATH_REGENERATE = "/api/v1/plan/{id}/regenerate"
PATH_PLAN_GET = "/api/v1/plan/{id}"
PATH_PLAN_STATUS = "/api/v1/plan/{id}/status"
PATH_EXPORT_PDF = "/api/v1/plan/{id}/export/pdf"
PATH_EXPORT_ICS = "/api/v1/plan/{id}/export/ics"
PATH_TRIPS = "/api/v1/trips"
PATH_TRIPS_GET = "/api/v1/trips/{id}"
PATH_TRIPS_SHARED = "/api/v1/trips/shared/{slug}"
PATH_ACCOUNT = "/api/v1/account"
PUBLIC_ORIGIN = "https://cuvoy.vercel.app"
ICS_FILENAME = "cuvoy-trip.ics"

# PROJECT_SPEC §9 — user-facing cost labels (never show raw enum)
COST_LABEL_UI = {
    "verified_fare": "Verified",
    "estimated_cost": "Estimated",
    "unavailable": "Unavailable",
}

AI_DISCLAIMER = (
    "Travel times, prices, and itineraries are estimates generated using AI and "
    "third-party mapping services. Please verify important details before travel."
)
