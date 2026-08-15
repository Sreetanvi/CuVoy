# CuVoy — Project Specification

**CuVoy — Curating One's Voyage**

Living document for product scope, architecture, rules, and integrations.
Last updated: 2026-08-14

> Detailed AI prompts, JSON schemas, pipeline architecture, model routing, and validation rules are preserved in [`docs/AI_ARCHITECTURE_REFERENCE.md`](docs/AI_ARCHITECTURE_REFERENCE.md).

---

## Table of Contents

1. [Vision](#1-vision)
2. [Scope & Business Model](#2-scope--business-model)
3. [Branding & Design](#3-branding--design)
4. [Input Context](#4-input-context)
5. [Rules & Logic](#5-rules--logic)
6. [Processing Pipeline](#6-processing-pipeline)
7. [Multi-Destination & Travel Days](#7-multi-destination--travel-days)
8. [Place Data Strategy](#8-place-data-strategy)
9. [Pricing Strategy](#9-pricing-strategy)
10. [Crowd Confidence Engine](#10-crowd-confidence-engine)
11. [Feature Requirements (V1)](#11-feature-requirements-v1)
12. [Auth, Access & Export](#12-auth-access--export)
13. [Group Planning](#13-group-planning)
14. [Reservations & Contact Info](#14-reservations--contact-info)
15. [Tech Stack](#15-tech-stack)
16. [Backend Architecture & Compute Strategy](#16-backend-architecture--compute-strategy)
17. [Caching Strategy](#17-caching-strategy)
18. [UI / UX Requirements](#18-ui--ux-requirements)
19. [Deployment & Infrastructure](#19-deployment--infrastructure)
20. [Legal & Compliance](#20-legal--compliance)
21. [AI Architecture Summary](#21-ai-architecture-summary)
22. [Benchmark Destinations](#22-benchmark-destinations)
23. [API Keys Checklist](#23-api-keys-checklist)
24. [Resolved Decisions](#24-resolved-decisions)
25. [Application Infrastructure Architecture (7.1–7.24)](#25-application-infrastructure-architecture-71-724)
26. [Changelog](#26-changelog)
27. [Routing & Optimization Architecture](#27-routing--optimization-architecture)
28. [GTFS Feed Registry](#28-gtfs-feed-registry)
29. [Validation & Data Processing](#29-validation--data-processing)
30. [AI Gateway — Rate Limit & Recovery](#30-ai-gateway--rate-limit--recovery)
31. [OSM Cache & Payload Architecture](#31-osm-cache--payload-architecture)
32. [Adaptive DBSCAN Clustering](#32-adaptive-dbscan-clustering)
33. [Matrix API Constraints](#33-matrix-api-constraints)
34. [Platform Reliability & Risk Mitigations](#34-platform-reliability--risk-mitigations)

---

## 1. Vision

CuVoy is a global, AI-powered travel planner that turns a natural-language trip request into a **feasible, costed, explainable day-by-day itinerary** with an interactive map showing routes, travel durations, and all stops.

**Core promise:** Geographic feasibility, realistic timing (dynamic transit buffers, meals, dwell time), grounded recommendations (open, in-season), transparent pricing, and crowd confidence — not a generic list of attractions.

**Planning scope:** Global. Accepts a city, state, or country and builds a plan. Supports multi-city and multi-country trips.

**Differentiators:**
- Suggest a primary plan plus nearby cities/places as add-or-swap options
- Crowd Confidence (not live crowd prediction)
- Hidden gems with explainability
- Dynamic replanning via editable Trip Controls
- Group planning, packing suggestions, reservation hints

---

## 2. Scope & Business Model

| Decision | Value |
|----------|-------|
| Pricing model | Free for users |
| API budget | Zero paid API usage — free tiers only |
| Geographic scope | Global |
| Trip types | Single-city, multi-city, multi-country |
| Destination input | City, state, or country |
| Auth default | Anonymous usage |
| Save / share trips | Login required (Supabase Auth) |
| Export | PDF, `.ics` calendar download |
| Plan credits | **3 plans per day** per user/IP (anonymous) or per account (logged in) |
| API spend policy | Free tiers only — never auto-upgrade to paid usage |

---

## 3. Branding & Design

| Item | Value |
|------|-------|
| App name | **CuVoy — Curating One's Voyage** |
| Logo | Convoy-themed circular logo (nature/road trip motif). Stored at `public/logo.png` |
| Light mode | White as primary background |
| Dark mode | Black as primary background |
| Accent colors | Green, brown, blue (nature-inspired hints) |
| Gradients | Strictly prohibited |
| Themes | Both light and dark mode supported |
| Domain | `cuvoy.vercel.app` |

---

## 4. Input Context

Every planning request is structured around:

| Field | Description | Example |
|-------|-------------|---------|
| `user_prompt` | Free-text trip request | *"2 weeks in Rajasthan, forts and food"* |
| `budget` | Daily spend in local currency | `₹5000/day` or `₹10000/day` |
| `transportation_preference` | How user moves between stops | See [Transport Preferences](#transport-preferences) |
| `travel_dates` | Start/end dates or duration | `2026-04-10` → `2026-04-13` |
| `location_data` | City, state, or country + radius | Rajasthan, India |

### Extracted Preferences (LLM → structured JSON)

- Budget (numeric daily value + currency; internally classified as low / mid / high)
- Dates (seasonality, holidays, festivals)
- Interests (history, food, nature, nightlife, shopping, etc.)
- Pace (relaxed / moderate / packed — default: **moderate**)
- Kids, elderly, accessibility needs
- Food preferences (dietary restrictions, cuisine types)
- Hidden gems preference
- Group composition (for group planning)

### Transport Preferences

**Question:** Do you have your own vehicle?

**If Yes — preferred vehicle (used for all legs by default):**
- Car
- Bike
- Camper
- Bicycle

**If No — default: Mixed.** User may override to:
- Walking
- Metro
- Taxi
- Bus

Vehicle ownership overrides default transport mode for the entire trip unless the user changes it per leg or in Trip Controls.

---

## 5. Rules & Logic

### 5.1 Geographic Feasibility

- Cluster daily activities by neighborhood.
- **Max intra-city transit** — user-selectable preset or custom:

| Preset | Max transit between consecutive stops |
|--------|----------------------------------------|
| Walkable | 15–20 min |
| Relaxed | 30 min |
| Balanced (default) | 40 min |
| Explorer | 60 min |
| No Limit | Unlimited |

- Custom max transit time is also supported via Trip Controls.
- Inter-town / inter-city moves are **travel days**, not counted against intra-city transit limits.
- Never schedule back-to-back activities exceeding the user's max transit unless designated as a travel day.

### 5.2 Transit Buffer (Dynamic by Mode)

Applied on top of base travel time from Mapbox Directions/Matrix:

| Mode | Buffer |
|------|--------|
| Walking | 5–10% |
| Personal vehicle (car, bike, camper, bicycle) | 10% |
| Taxi / Uber | 15% |
| Public transport (metro, bus, mixed) | 20–25% |

### 5.3 Day Schedule Defaults

All itinerary times are expressed in **destination-local time**, not the user's home timezone.

| Setting | Default | Override |
|---------|---------|----------|
| Day start | 09:00 local | User preference; earlier for sunrise/breakfast spots |
| Day end | 21:00 local | User preference |
| Pace | Moderate | Trip Controls |
| Timezone | Resolved from destination coordinates | Stored as IANA timezone ID per trip/day |

**Example:** A user in Mumbai planning a trip to Tokyo sees `09:00` as **09:00 JST (Tokyo time)**, not IST. Meal windows, opening hours, sunrise/sunset, and transit schedules all use the destination timezone.

### 5.4 Default Dwell Times by Category

| Category | Default dwell |
|----------|---------------|
| Museum | 2 hours |
| Viewpoint | 30 minutes |
| Restaurant | 90 minutes |

Dwell, wait, and spending time at each stop must appear explicitly in the itinerary.

### 5.5 Meal Windows

Meal windows are editable in the itinerary UI. Defaults:

| Meal | Default window | Minimum duration |
|------|----------------|------------------|
| Lunch | 13:00–14:00 (1–2 hr window, customizable) | 60 minutes |
| Dinner | 19:00–21:00 (customizable) | 60 minutes |

**Lunch block UI example:**

```
Lunch
━━━━━━━━━━━━━━
12:45–2:00 PM

Suggested:
• ABC Restaurant
• XYZ Cafe

[Change Time]  [Change Restaurant]  [Skip Lunch]
```

Same pattern for dinner. Changing time or restaurant triggers adaptive replanning of the remaining day.

### 5.6 Grounding

- Do not suggest permanently closed or out-of-season places.
- Validate opening hours before scheduling.
- When asked, explain why a place was excluded.
- If opening hours cannot be verified, show a verification warning — never guess.

### 5.7 Conflict Detection

- Warn if an attraction closes before estimated arrival.
- Flag places where a reservation is likely needed.

### 5.8 Explainability

Every recommendation includes a short reason:

> *"Chosen because it's 8 minutes from your previous stop, fits your budget, and matches your interest in history."*

### 5.9 Adaptive Replanning

- Skip a stop, change meal time, change max transit, or swap a place → regenerate **only the remaining itinerary**.
- Trip Controls changes trigger regeneration in seconds.
- Locked activities are preserved during partial regeneration.

### 5.10 Alternative Suggestions

After generating a plan, suggest:
- Nearby cities worth adding
- Nearby places as add-or-swap options for existing stops

---

## 6. Processing Pipeline

### Routing vs Optimization (critical distinction)

| Engine | Role | Provider |
|--------|------|----------|
| **Routing engine** | Travel times, distances, route geometry | **Mapbox** (Matrix + Directions) |
| **Optimization engine** | Optimal visit order, constraint scheduling | **OR-Tools** |

CuVoy does **not** implement road-network routing from scratch. Mapbox provides the travel-time/distance matrix and final route polylines; OR-Tools consumes that matrix to determine stop order.

### Routing & Optimization Flow

```
Places (reduced candidate set)
        ↓
Mapbox Matrix API
        ↓
Travel-time / distance matrix
        ↓
OR-Tools
        ↓
Optimal visit order
        ↓
Mapbox Directions API
        ↓
Actual route geometry + leg details
```

### Full Pipeline

```
User Prompt
    ↓
Extract Preferences (LLM)
    ↓
Destination Classification & Planning (city / state / country / multi-city)
    ↓
Find Candidate Places (Mapbox Search)
    ↓
Enrich Metadata (OpenStreetMap Overpass — city/region batch)
    ↓
Verify Hours / Closed Status (official website if available)
    ↓
Remove closed / out-of-season places
    ↓
Candidate Ranking (interests, budget, crowd, hidden gems)
    ↓
Candidate Reduction (local filter — BEFORE Matrix API)
    ↓
H3 Spatial Indexing
    ↓
DBSCAN Geographic Clustering
    ↓
Mapbox Matrix API (reduced candidate set only) → travel-time matrix
    ↓
OR-Tools Optimization → optimal visit order
    ↓
Mapbox Directions API → route geometry + leg details
    ↓
Detect Travel Days (inter-city legs)
    ↓
Add Meals & Breaks
    ↓
Estimate Costs (formula-based, no AI)
    ↓
Crowd Confidence Scoring
    ↓
Weather Integration (Open-Meteo forecast + historical climate)
    ↓
Generate Itinerary Narrative (LLM)
    ↓
Packing List (LLM)
    ↓
Explainability & Exclusion Reasons (LLM)
    ↓
Cross-Schema Validation
    ↓
Render Map (Mapbox Maps SDK) + Itinerary UI
```

**Architectural principle:** LLMs reason; Mapbox routes; OR-Tools optimizes; deterministic algorithms validate. The LLM never invents places, coordinates, hours, travel times, or factual prices.

---

## 7. Multi-Destination & Travel Days

### Destination Input Modes

- Single city
- Multiple cities (same state/country)
- State or region
- Country
- Multi-country

### Auto-Detected Travel Day Sequence

When moving between cities, the system automatically structures:

```
Travel Day
    ↓
Hotel Checkout
    ↓
Train / Flight / Drive (inter-city transit)
    ↓
Lunch (en route or at destination)
    ↓
Hotel Check-in
    ↓
Evening Activity (light, near hotel)
```

Travel days are excluded from intra-city transit limits and neighborhood clustering rules.

---

## 8. Place Data Strategy

### Data Flow

```
Mapbox Search API
    ↓
Get Places
    ↓
OpenStreetMap Overpass API (city/region batch — NOT per-attraction)
    ↓
Cached POI dataset → local candidate filtering
    ↓
Opening hours, category, extra metadata
    ↓
Official Website (if available)
    ↓
Verify hours / closed status
    ↓
If data missing → show verification warning (never guess)
```

### Source Priority

| Role | Source |
|------|--------|
| Primary discovery | Mapbox Search API |
| Validation & enrichment | OpenStreetMap Overpass API |
| Hours verification | Official attraction website (when available) |
| Supplementary metadata | OpenTripMap API, GeoNames, Wikimedia / Wikipedia API |
| Fallback behavior | Show *"Opening hours couldn't be verified"* warning |

### Trust Hierarchy

1. **Official sources** — attraction website, government tourism site, park/museum site
2. **Verified APIs** — Mapbox, OpenStreetMap, OpenTripMap, Open-Meteo, Nager.Date, Sunrise-Sunset.org, GTFS fare data
3. **Internal business logic** — crowd estimation, budget estimation, transit buffers
4. **LLM reasoning** — only when facts unavailable; must state *"Unable to verify"* instead of fabricating

### OSM Overpass Batching Strategy

Do **not** query Overpass per attraction. Batch by city/region:

```
City / Region boundary
        ↓
Single Overpass query (or cache hit)
        ↓
Cached POI dataset (Upstash, 30 days)
        ↓
Local candidate filtering (no additional API calls)
        ↓
Enriched candidates proceed to ranking
```

This keeps OSM usage within free-tier limits and aligns with the per-plan API budget.

---

## 9. Pricing Strategy

All pricing follows a **show-only-when-trustworthy** policy. CuVoy never invents numbers to fill UI boxes.

### Cost Display Toggle

Transport costs are **opt-in**. The user enables them in Trip Controls:

```
Show estimated transport cost   [ OFF / ON ]
```

| Toggle state | Behavior |
|--------------|----------|
| OFF | No transport cost shown anywhere (itinerary, map popup, PDF, totals) |
| ON | Show costs only where reliable data exists; otherwise show "Cost unavailable" |

Activity, meal, and accommodation costs follow separate rules (see below). The toggle applies specifically to **transport leg costs**.

### Three-Tier Cost Labels (UI must always distinguish)

| Label | Meaning | When used |
|-------|---------|-----------|
| **Verified fare** | Based on published fare data (GTFS or official transit authority) | GTFS fare_rules or official source confirmed |
| **Estimated cost** | Calculated from configured formulas (per-km rates, price levels) | Deterministic estimate with known inputs |
| **Unavailable** | No trustworthy data exists | GTFS missing, no official fare, no configured formula |

**Never:** LLM invents a number just to fill the box.

### Transport Cost Decision Flow

```
User enables "Show estimated transport cost"
          ↓
     What transport mode?
          ↓
 ┌────────┼───────────┐
 │        │           │
Walk    Public       Taxi /
        Transit       Car
 │        │           │
₹0       GTFS /       Verified or
         official     configured
         fare data    per-km estimate
          │
          ▼
    Is reliable data available?
       /       \
     YES        NO
      │          │
      ▼          ▼
 Show cost   "Cost unavailable"
 (with label)  (no number shown)
```

| Mode | Data source | Display label |
|------|-------------|---------------|
| Walking | Always zero | Verified fare (₹0) |
| Public transit | GTFS fare data or official authority source | Verified fare |
| Public transit (no GTFS) | — | **Cost unavailable** — plan still works via walk/drive/taxi |
| Taxi / rideshare | Configured base + per-km formula | Estimated cost |
| Personal vehicle (car, bike, etc.) | Configured per-km formula | Estimated cost |

### GTFS Coverage Policy

| City GTFS coverage | CuVoy behavior |
|--------------------|----------------|
| Excellent GTFS (fare data included) | Public transit legs show **Verified fare** |
| GTFS routes only (no fares) | Public transit legs show **Cost unavailable**; plan using transit times still works |
| No GTFS at all | No public transit cost shown; CuVoy plans using walk / drive / taxi per user preference — never pretends reliable transit fare data exists |

GTFS feeds fetched on demand per city and cached (30 days). No mandatory preload registry — benchmark cities tested at build time, feeds discovered dynamically.

### A. Transport (formula-based, toggle-gated)

| Mode | Method |
|------|--------|
| Car / personal vehicle | Base fare + per-km rate (from distance via Mapbox) |
| Metro / Bus | GTFS fare data or official transit authority fare source |
| Taxi / Uber | Base fare + per-km estimate |
| Walking | ₹0 / local currency 0 |

#### Transit Fare Resolution

Not every transit system publishes complete GTFS fare data. CuVoy resolves fares deterministically:

```
                    Fare
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
       GTFS fare          Official fare
        available            source
           │                   │
           └─────────┬─────────┘
                     ▼
                Verified Fare
                     │
                     ▼
                 Use it

If neither exists → "Fare unavailable" (V1)
Never: LLM → "I think the metro costs ₹40"
```

**Flow:**
```
Official fare / GTFS
        ↓
Structured fare data
        ↓
Deterministic calculation
        ↓
AI explanation (narrative only — not the price itself)
```

For cities without GTFS or official fare data, display **"Cost unavailable"** — the trip plan is unaffected; only the cost box is hidden.

### B. Restaurants

Estimate from price level (not exact menu prices):

| Price level | Estimate range |
|-------------|----------------|
| Low | Budget dining range |
| Mid | Mid-range dining range |
| High | Premium dining range |

### C. Activities

Estimate from category + price level when available. Show range when exact price unknown.

### D. Budget Input

Users enter a daily amount (e.g. `₹5000/day`, `₹10000/day`). Internally classified:

| Internal tier | Typical use |
|---------------|-------------|
| Low | Budget-conscious selections |
| Mid | Balanced mix |
| High | Premium experiences |

Display: individual cost (with label: Verified / Estimated / Unavailable), daily total, trip total, cost confidence, and currency. Trip total excludes transport costs when toggle is OFF or data is unavailable.

---

## 10. Crowd Confidence Engine

**Terminology:** Use **"Crowd Confidence"**, not "Crowd Prediction." Never present estimates as live measurements.

### Inputs

- Weekday vs weekend (+25 for Sat/Sun)
- Public holidays (+30) — Nager.Date API
- Local festivals (+40) — calendar + AI reasoning (e.g. Hindu festival → temples crowded)
- Local events (+35)
- Peak tourist season (+20)
- School holidays
- Weather (rain at beach → empty; rain → museums less crowded)
- Time of day (opening hour +15, closing hour -15)
- Attraction category (Friday → more crowd near mosques/temples)
- Sunny weather at beach (+10)
- Heavy rain (-20)

### Output

```
Very Quiet | Quiet | Moderate | Busy | Very Busy
```

Each score includes:
- Confidence level: High / Medium / Low
- Transparent reason list (e.g. "Saturday + National Holiday + Sunny Weather")

### Supporting APIs

- Nager.Date (public holidays)
- Open-Meteo Forecast API (near-term trips)
- Open-Meteo Historical Weather API (ERA5/ERA5-Land reanalysis — monthly/climatological baselines when forecast unavailable)
- Sunrise-Sunset.org (sunrise/sunset for beach/timing decisions)
- Wikimedia / Wikipedia (context)
- GeoNames, OpenTripMap (supplementary)

---

## 11. Feature Requirements (V1)

| Feature | Included |
|---------|----------|
| Global planning | Yes |
| Multi-city / multi-country trips | Yes |
| AI itinerary generation | Yes |
| Interactive map with routes & durations | Yes |
| Route optimization (OR-Tools) | Yes |
| Budget estimation | Yes |
| Crowd Confidence | Yes |
| Hidden gems | Yes |
| Explainability per stop | Yes |
| Dynamic replanning | Yes |
| Trip Controls panel (inline editing) | Yes |
| Alternative cities / swap suggestions | Yes |
| Group planning | Yes |
| Packing list | Yes |
| Reservation hints | Yes |
| PDF export | Yes |
| `.ics` calendar download | Yes |
| Anonymous usage | Yes |
| Login to save / share | Yes |
| Light + dark mode | Yes |

**Deferred beyond V1:** Live reservation booking integration, full offline map tiles, Google Calendar OAuth sync.

---

## 12. Auth, Access & Export

### Auth Model

| Flow | Behavior |
|------|----------|
| First visit | Anonymous — can generate itineraries immediately |
| Save trip | Prompt login |
| Share trip | Requires account |
| Providers | **Email + Google** (Supabase built-in) |
| Email service | Supabase built-in email auth only — no third-party email provider unless limits are hit |

### Save Trip Modal

```
┌─────────────────────────┐
│      Save your trip     │
├─────────────────────────┤
│                         │
│  [ Continue with Google ]│
│                         │
│  ─────── or ───────     │
│                         │
│  Email                  │
│  Password               │
│                         │
│  [ Create account ]     │
└─────────────────────────┘
```

### Export — PDF

- Text itinerary (day-by-day schedule with times, costs, notes)
- Map route snapshot with average travel times labeled along the route
- CuVoy logo in a corner
- AI disclaimer footer

### Export — Calendar (`.ics`)

CuVoy generates `cuvoy-trip.ics` as a file download. No Google Calendar OAuth in V1.

```
User clicks Download Calendar
        ↓
cuvoy-trip.ics downloaded
        ↓
User double-clicks file
        ↓
Google Calendar / Apple Calendar / Outlook
        ↓
Events imported
```

Each itinerary stop becomes a calendar event with start/end time, location, and notes.

### Data Deletion

GDPR basic — user can delete account and all trip data from profile settings.

---

## 13. Group Planning

### UX — Toggle

Group Planning is a toggle in Trip Controls:

```
Group Planning
       OFF / ON
```

When **ON**:

```
┌─────────────────────────────────────┐
│ Group Planning                      │
│                                     │
│ Travelers: 4                        │
│                                     │
│ Planning priority:                  │
│                                     │
│ ○ Everyone                          │
│   Consider everyone's interests     │
│                                     │
│ ○ Team Lead                         │
│   Prioritize team lead's interests  │
└─────────────────────────────────────┘
```

Each traveler has a name (optional) and interest tags. The team lead is designated when "Team Lead" mode is selected.

### How Group Planning Works

Simply passing all interests to an LLM is not sufficient. CuVoy uses deterministic scoring with LLM-assisted ranking.

**Example group:**
- Person A → History
- Person B → Food
- Person C → Nature
- Person D → Shopping

#### Mode 1 — Everyone's Interests

Maximize **group satisfaction**. The itinerary balances coverage across all interests:

```
Morning  → Heritage
Lunch    → Food
Afternoon → Nature
Evening  → Shopping
```

Optimization objective:

```
Group Score =
  interest coverage
  + preference satisfaction
  + geographic efficiency
  + budget fit
```

Each person's interests contribute equally to the score.

#### Mode 2 — Team Lead

Team lead preferences receive higher weight:

```
Lead weight  = 50%
Others weight = 50% collectively (split among remaining travelers)
```

The optimizer prioritizes stops matching the lead's interests while ensuring minimum coverage for others.

### Implementation Notes

- Interest tags per traveler stored in trip preferences JSON
- Group score computed deterministically during candidate ranking and OR-Tools optimization
- LLM generates narrative explaining how the plan balances group needs
- Group settings editable in Trip Controls; changes trigger replan

---

## 14. Reservations & Contact Info

CuVoy does **not** integrate live booking in V1. Instead, it surfaces contact/reservation guidance per stop.

### When official website exists but no online booking

```
Official website: [Visit website]
Reservations: Contact the attraction through the official website.
```

### When phone number is available

```
Official website: [Visit website]
Phone: +XX XXXXXXXX
Reservations: Contact the attraction by phone or through their website.
```

### When neither website nor phone is found

```
Reservation contact information not found.
```

Never fabricate booking links or phone numbers. Flag stops where reservations are likely needed (fine dining, popular museums, timed-entry attractions) based on category rules.

---

## 15. Tech Stack

### Frontend

| Layer | Choice |
|-------|--------|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| UI | React |
| Styling | Tailwind CSS |
| Components | shadcn/ui |
| Animation | Framer Motion |
| Data fetching | TanStack Query |

### Backend

| Layer | Choice |
|-------|--------|
| API | FastAPI (Python) on **Render** |
| Optimization | Google OR-Tools |
| Clustering | DBSCAN + H3 (Uber H3) |
| Caching | Redis via Upstash |
| Job execution | On-demand request handlers only — no permanent background workers |

### Database, Storage & Auth

| Layer | Choice |
|-------|--------|
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth (Email + Google) |
| Storage | Supabase Storage (PDF exports, assets) |

### Maps & Location

| Service | API | Role |
|---------|-----|------|
| Map rendering | Mapbox Maps SDK | Interactive map, markers, routes |
| Place search | Mapbox Search API | Candidate POI discovery |
| Geocoding | Mapbox Geocoding API | Address ↔ coordinates |
| **Routing engine** | **Mapbox Matrix API** | Pairwise travel times / distances (input to OR-Tools) |
| **Routing engine** | **Mapbox Directions API** | Route geometry + leg details (after OR-Tools ordering) |
| **Optimization engine** | **Google OR-Tools** | Optimal visit order (does not compute routes) |

### External Data APIs (all free tier)

| Service | Use | Key required |
|---------|-----|--------------|
| OpenStreetMap Overpass | Hours, categories, metadata | No |
| Open-Meteo Forecast API | Current weather forecast | No |
| Open-Meteo Historical Weather API | ERA5/ERA5-Land reanalysis; global data back to 1940; climatological baselines for dates beyond forecast horizon | No |
| Nager.Date | Public holidays | No |
| Sunrise-Sunset.org | Sunrise/sunset times | No |
| OpenTripMap | Supplementary POI data | Yes (free key) |
| GeoNames | Geographic metadata | Yes (free key) |
| GTFS feeds | Transit fare data (where published) | No (public feeds) |
| Wikimedia / Wikipedia | Context, descriptions | No |

### AI (free tier only)

| Provider | Role |
|----------|------|
| Google Gemini (free) | Primary LLM |
| Groq (free) | Fallback |
| OpenRouter (free models) | Secondary fallback |
| Deterministic fallback | When all LLM providers unavailable |

All AI calls route through a single **AI Gateway → Model Router** (see AI Architecture Reference).

---

## 16. Backend Architecture & Compute Strategy

### Hosting Decision

**Render** hosts the FastAPI backend (replacing Railway). Render's free tier is suitable for CuVoy V1 with strict compute and memory discipline.

| Render free-tier constraint | Implication for CuVoy |
|----------------------------|------------------------|
| **Spin-down after 15 minutes** of inactivity | Web service sleeps; first request after idle triggers a cold start |
| **512 MB RAM hard cap** | OR-Tools, GTFS parsing, and in-memory matrices must stay strictly bounded |
| **Limited CPU / hours** | No permanent workers; cache-first; stage checkpointing |
| **Single web service** | All backend logic in one FastAPI process |

CuVoy must minimize backend compute and memory. See [Section 18](#18-ui--ux-requirements) for cold-start UX and [7.8](#78-cicd-architecture) for the keep-alive workflow.

### Memory Constraints (512 MB)

Render's free tier enforces a **512 MB RAM hard cap** (same practical limit as Railway free tier). The backend must:

- Run OR-Tools on **post-reduction** candidate sets only (typically ≤20 stops/day)
- **Never** load full GTFS CSVs into Pandas at runtime — preprocess offline
- Keep active pipeline state compact; offload large blobs to Upstash
- Limit concurrent generation jobs to avoid memory stacking
- Cap OR-Tools solver timeout at 10 seconds

### Architecture

```
Frontend (Vercel)
        ↓
Render FastAPI (stateless, on-demand)
        ↓
    ┌───┴───┐
    ▼       ▼
Supabase  Upstash
    ↓       ↓
External APIs (Mapbox, OSM, Open-Meteo, LLM, etc.)
```

### Compute Minimization Rules

| Rule | Rationale |
|------|-----------|
| No permanent background workers | Render free tier cannot sustain always-on workers |
| Stateless FastAPI handlers | Each request is self-contained; no in-process state |
| Offload persistence to Supabase | DB reads/writes go directly to Supabase, not held in memory |
| Offload caching to Upstash | All cache reads/writes via Upstash REST — no local Redis |
| Heavy computation only on user request | OR-Tools, clustering, matrix fetches triggered by explicit user action |
| Cache aggressively | Reuse places, matrix, geocoding, weather from Upstash (see caching section) |
| Frontend does rendering | Map rendering, PDF preview generation lean toward client-side where possible |
| LLM calls batched per pipeline stage | Minimize round-trips; one structured call per stage |
| Regeneration reuses cached data | Partial replan reads cached matrix/places instead of re-fetching |
| Candidate reduction before Matrix | Shrink candidate set locally before any Matrix API call |
| Per-plan API budget | Every plan gets an internal budget envelope; regeneration uses a fractional sub-budget |

### Plan Credits & API Budget

**User-facing limit:** 3 plan credits per day (per IP for anonymous users; per account for logged-in users).

```
3 PLAN CREDITS / DAY
        │
        ▼
┌───────────────────┐
│ Planning Budget   │
└─────────┬─────────┘
          │
          ▼
      Plan #1
          │
          ├── LLM budget
          ├── Mapbox budget
          ├── OSM budget
          ├── Weather budget
          └── Verification budget
```

| Action | Credit / budget impact |
|--------|------------------------|
| **New plan** | Consumes **1 planning credit** + full internal API budget envelope |
| **Regeneration** (Trip Controls edit, skip stop, swap) | Consumes **fractional internal API budget** only; no additional user-facing credit if within regeneration allowance |
| **Export** (PDF / `.ics`) | No planning credit consumed |

Each plan run tracks spend against per-provider sub-budgets. If a sub-budget is exhausted mid-plan, CuVoy uses cache → alternate free provider → deterministic fallback → graceful partial result (never paid tier).

### Free-Tier Hard Stop Policy

CuVoy must **never** automatically transition from a free tier into paid usage. When a free-tier quota is exhausted:

1. Disable that provider for the affected operation
2. Attempt cache hit
3. Attempt alternate free provider
4. Fall back to deterministic logic
5. If all fail, temporarily reject the operation with a user-visible message

### Request Lifecycle (no workers)

```
User action (generate / replan / export)
        ↓
Next.js API route or direct FastAPI call
        ↓
Check Upstash cache
        ↓ (cache miss)
FastAPI pipeline (single request, async where possible)
        ↓
Write results to Upstash + Supabase
        ↓
Return JSON to frontend
```

Long-running generations use FastAPI `BackgroundTasks` within the same request lifecycle, not separate worker processes. If a request exceeds Render timeout, the pipeline must be split into cacheable stages that can resume.

---

## 17. Caching Strategy

**Provider:** Upstash Redis

### Should Cache

| Data | TTL |
|------|-----|
| Places (Search API results) | 30 days |
| Geocoding | 90 days |
| Matrix API | 24 hours |
| Directions | 1–6 hours (shorter when traffic-sensitive) |
| Weather | 15–30 minutes |
| GTFS fare data | 30 days |
| AI itineraries | 7 days (only when exact request repeats) |
| AI responses | Cache only on exact duplicate request |
| Public holidays (Nager.Date) | 30 days |
| Computation results (H3, DBSCAN, OR-Tools) | Session / until inputs change |
| OSM POI datasets (city/region batch) | 30 days |

### Should NOT Cache (or very short TTL)

| Data | Policy |
|------|--------|
| User profile edits | Never cache — write-through to Supabase |
| Live traffic | Do not cache, or max 2–5 minutes |
| Booking availability | Do not cache |
| Real-time flight prices | Do not cache |
| Live hotel prices | Do not cache |
| Session / regeneration state | In-memory or Redis session TTL until logout |

### Cache Layers

1. **API/Data Cache** — external API responses (places, routes, weather, holidays, GTFS)
2. **Computation Cache** — H3 indexes, clusters, optimization results, crowd scores
3. **Session/Itinerary Cache** — current trip state, regeneration context, locked activities

---

## 18. UI / UX Requirements

**Landing Page & Onboarding Vision**
The application must include an immersive landing page that serves as the entry point. This cinematic screen must appear **every time** the website is freshly opened.

**Visuals & Assets (Target Directory: `/public` at the project root)**
* **Backgrounds:** The background will smoothly crossfade between our core visual themes using the following image files:
  * `ticket_backg` (Chaotic travel/collage vibe)
  * `road_backg` (Serene adventure/coastal road vibe)
  * `map_backg` (Tactile planning aesthetic)
* **Typography:** The primary heading text must use a scrapbook/ransom-note font aesthetic. Please analyze the image named font (located in the root /public directory) and use it as the exact visual reference to match this tactile, personalized travel journal style.

**Copy / Text Structure:**
* **Title:** CuVoy
* **Subtitle:** Curating your Voyage
* **Tagline:** Plot your escape

**Animation & User Flow:**
1. **Initial State:** The user lands on the page featuring the alternating backgrounds and the primary text block (Title, Subtitle, Tagline).
2. **Transition:** After a brief delay, the entire text block smoothly swipes/slides upwards.
3. **Call to Action (CTA):** A primary button fades in underneath, reading **"Start Curating"**.
4. **Handoff:** Clicking the "Start Curating" button dissolves the landing page graphics and transitions the user directly into the main chat interface to begin their planning session.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Header: CuVoy logo, saved trips, profile / login                │
├────────────────────────────┬─────────────────────────────────────┤
│                            │                                     │
│   MAP PANEL                │   ITINERARY PANEL                   │
│   • Markers for all stops  │   • Day-by-day timeline             │
│   • Route polylines        │   • Transit legs + durations        │
│   • Travel durations       │   • Meal blocks (editable)          │
│   • Click → stop detail    │   • Costs + Crowd Confidence        │
│                            │   • Explainability snippets         │
│                            │   • Conflict / reservation warnings │
│                            │   • Swap / add suggestions          │
├────────────────────────────┴─────────────────────────────────────┤
│  TRIP CONTROLS (collapsible sidebar panel — NOT hidden settings) │
│  Max Transit | Pace | Day Start/End | Lunch/Dinner windows      │
│  Transport mode | Budget | Hidden gems | Group Planning toggle │
├──────────────────────────────────────────────────────────────────┤
│  Input: prompt + destination + dates + budget + vehicle question │
└──────────────────────────────────────────────────────────────────┘
```

### Trip Controls Panel

After itinerary generation, all key settings are editable in a collapsible **Trip Controls** panel on the side. Changes trigger fast regeneration (seconds, not full reload).

Editable controls:
- Max transit preset or custom value
- Pace
- Day start / end times
- Lunch and dinner windows
- Transport mode
- Daily budget
- Hidden gems mode
- Group Planning toggle + traveler interests + priority mode
- **Show estimated transport cost** toggle (OFF by default)
- Accessibility preferences

### Map Panel

- All stops for selected day (toggle full trip view)
- Route polyline with buffered travel durations per leg
- Marker click → popup: name, cost (with Verified/Estimated/Unavailable label), reason, hours, crowd confidence, warnings, reservation info

### Responsive

- Desktop: map + itinerary side-by-side
- Mobile: tabbed or bottom-sheet map; itinerary primary

### Backend Cold Start UX (Render spin-down)

Render free-tier web services **spin down after 15 minutes of inactivity**. The first plan request after sleep may take **45–60 seconds** while the container wakes.

The Next.js frontend **must** handle this gracefully:

| State | UI behavior |
|-------|-------------|
| Backend waking (cold start) | Show friendly loading: **"Waking up the AI planner…"** with progress animation |
| Backend warm | Show normal pipeline progress via SSE ("Understanding preferences…", etc.) |
| Cold start + planning | Do **not** show raw errors or timeouts during wake; extend client timeout for first request |
| Retry | If wake fails, offer "Try again" — second attempt is usually fast if service stayed warm |

Implementation notes:

- Detect cold start via slow initial `GET /health` or first `/api/v1/plan` latency
- TanStack Query / fetch wrapper should use **≥90s timeout** for first request after idle
- Keep normal generation timeout at ~30s once backend is warm
- Optional: ping `/health` on app load (lightweight) to pre-warm before user clicks Generate

---

## 19. Deployment & Infrastructure

| Component | Platform |
|-----------|----------|
| Frontend | Vercel (`cuvoy.vercel.app`) |
| Backend API | **Render** (FastAPI web service) |
| Database + Auth | Supabase |
| Redis cache | Upstash |
| Primary region | Mumbai (closest available) |
| Fallback region | Singapore |

### Environment Variables by Platform

| Platform | Variables | Where configured |
|----------|-----------|------------------|
| **Vercel** | `NEXT_PUBLIC_*` (Supabase URL/anon, Mapbox public token, FastAPI URL) | Vercel project dashboard → Environment Variables |
| **Render** | All private backend secrets (LLM keys, service role, Upstash, etc.) | **Render dashboard** → Web Service → Environment |
| **Local dev** | `.env.local` (frontend), `.env` (backend) | Git-ignored files only |
| **Supabase Auth** | Google OAuth client ID/secret | Supabase dashboard → Authentication → Providers |

**Never commit real API keys to markdown files or git.** Use `.env.example` with empty placeholders only.

### Environment Variables (overview)

```bash
# ── Vercel (frontend — NEXT_PUBLIC_* only) ──
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=
NEXT_PUBLIC_FASTAPI_URL=https://your-render-service.onrender.com

# ── Render (backend — private, Render dashboard) ──
MAPBOX_ACCESS_TOKEN=
SUPABASE_SERVICE_ROLE_KEY=
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
GEMINI_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
OPENTRIPMAP_API_KEY=
GEONAMES_USERNAME=
FASTAPI_SECRET_KEY=
CORS_ORIGINS=https://cuvoy.vercel.app
```

---

## 20. Legal & Compliance

| Requirement | Implementation |
|-------------|----------------|
| Privacy Policy | Required — state what data is collected and how it is used |
| GDPR (basic) | Allow account + data deletion; clear consent for saved trips |
| AI Disclaimer | *"Travel times, prices, and itineraries are estimates generated using AI and third-party mapping services. Please verify important details before travel."* |
| Mapbox attribution | Required on all map views |
| Cost disclaimer | Three-tier labels (Verified / Estimated / Unavailable); transport costs opt-in via toggle; never LLM-guessed |

---

## 21. AI Architecture Summary

Full prompts, JSON schemas, validation pipelines, model routing matrices, and failure/fallback architecture are in [`docs/AI_ARCHITECTURE_REFERENCE.md`](docs/AI_ARCHITECTURE_REFERENCE.md).

### Core Principle

| Layer | Responsibility |
|-------|----------------|
| LLM | Preference extraction, ranking nuance, narrative, explainability, packing, crowd reasoning |
| APIs | Places, hours, weather, holidays, routes, GTFS fares |
| Algorithms | H3, DBSCAN, OR-Tools, cost formulas, crowd scoring, group score |
| Validation | Schema checks, geographic feasibility, hours conflicts |

### AI Gateway & Model Router

```
All AI services → AI Gateway → Model Router
                                    ↓
                          Gemini Free (primary)
                                    ↓
                          Groq Free (fallback)
                                    ↓
                          OpenRouter Free (fallback)
                                    ↓
                          Deterministic fallback (no LLM)
```

**Constraints:** Zero paid LLM usage. Quota-aware routing. Token/call budgets per task. Structured JSON output validation.

---

## 22. Benchmark Destinations

CuVoy is validated against diverse destinations (not tuned to a single city):

| Destination | Tests |
|-------------|-------|
| **Bengaluru** | Dense urban travel, traffic, restaurants, public transport, GTFS |
| **Jaipur** | Heritage tourism, forts, museums |
| **Tokyo** | Efficient public transport, dense attractions, GTFS |
| **Interlaken** | Nature, long-distance travel |
| **Paris** | Walking-heavy cultural tourism |

---

## 23. API Keys Checklist

Set up these accounts and send the keys when ready. All must remain on **free tiers**.

### Required (must have before build)

| # | Service | Sign up | Env variable | Free tier notes |
|---|---------|---------|--------------|-----------------|
| 1 | **Mapbox** | [mapbox.com](https://www.mapbox.com) | `MAPBOX_ACCESS_TOKEN` | 100k map loads/mo, 100k geocoding/mo |
| 2 | **Supabase** | [supabase.com](https://supabase.com) | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | 2 free projects, 500 MB DB |
| 3 | **Upstash Redis** | [upstash.com](https://upstash.com) | `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` | 10k commands/day free |
| 4 | **Google Gemini** | [aistudio.google.com](https://aistudio.google.com) | `GEMINI_API_KEY` | Free tier with daily quotas |
| 5 | **Render** | [render.com](https://render.com) | Managed in Render dashboard (no key in repo) | Free tier — 512 MB RAM, spins down after 15 min idle |
| 6 | **Google OAuth** | Google Cloud Console | Configured in Supabase Auth dashboard | Free |

### How to Provide API Keys (never in markdown)

| Context | Where keys go | Never |
|---------|---------------|-------|
| **Local development** | `.env` / `.env.local` (git-ignored) | Commit to git or paste in PROJECT_SPEC |
| **Build agent / Cursor chat** | Paste keys directly in chat when agent asks, or add to local `.env` | Commit keys to repo |
| **Production frontend** | Vercel dashboard → Environment Variables | Hardcode in source |
| **Production backend** | **Render dashboard** → Web Service → Environment | Hardcode in source or md files |
| **CI/CD (keep-alive only)** | GitHub Actions secrets: `RENDER_HEALTH_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Log secrets in workflow output |

The spec lists **variable names** and **accounts to create** — not secret values.

### Required for AI fallback (recommended)

| # | Service | Env variable |
|---|---------|--------------|
| 7 | **Groq** | `GROQ_API_KEY` |
| 8 | **OpenRouter** | `OPENROUTER_API_KEY` |

### Recommended supplementary (free)

| # | Service | Env variable |
|---|---------|--------------|
| 9 | **OpenTripMap** | `OPENTRIPMAP_API_KEY` |
| 10 | **GeoNames** | `GEONAMES_USERNAME` |

### No key required

| Service | Use |
|---------|-----|
| OpenStreetMap Overpass | Hours, categories |
| Open-Meteo Forecast API | Current weather forecast |
| Open-Meteo Historical Weather API | ERA5 reanalysis; climate baselines for dates beyond forecast horizon |
| Nager.Date | Public holidays |
| Sunrise-Sunset.org | Sun times |
| GTFS feeds | Transit fares (public, per-agency) |
| Wikimedia / Wikipedia | Descriptions |

### Deployment accounts

| Service | Purpose |
|---------|---------|
| **Vercel** | Frontend hosting |
| **Render** | Backend FastAPI hosting |
| **GitHub** | Source control + CI/CD + keep-alive workflow |

### NOT needed

| Service | Reason |
|---------|--------|
| TimeZoneDB | Replaced by `timezonefinder` + `zoneinfo` |
| Google Places API | Paid — using Mapbox + OSM |
| Google Calendar API | `.ics` download replaces OAuth for V1 |
| Fly.io | No suitable free plan — using Render |
| Railway | Replaced by Render for backend hosting |
| Third-party email provider | Supabase built-in auth email sufficient for V1 |

---

## 24. Resolved Decisions

All previously open items are now decided. Reference sections for implementation detail.

| Topic | Decision | Reference |
|-------|----------|-------------|
| Plan credits | 3 plans/day per IP or account | [Section 16](#16-backend-architecture--compute-strategy) |
| Render spin-down / cold start | 15 min idle sleep; frontend "Waking up the AI planner…" UX; keep-alive workflow | [Section 18](#18-ui--ux-requirements), [7.8](#78-cicd-architecture) |
| Render timeout / chunking | Stage-based jobs with Upstash checkpoints | [7.2](#72-background-job--planning-queue-architecture), [7.13](#713-real-time-progress--replanning-architecture) |
| GTFS handling | On-demand fetch + cache; graceful degradation; feed registry schema | [Section 28](#28-gtfs-feed-registry) |
| PDF map render | Client-side canvas export (preferred) | [7.15](#715-share--export-architecture) |
| Job sequence | 10-step API lifecycle with SSE progress | [7.22](#722-complete-api-lifecycle-architecture) |
| Transport cost display | Opt-in toggle; Verified / Estimated / Unavailable labels | [Section 9](#9-pricing-strategy) |
| Routing vs optimization | Mapbox routes; OR-Tools optimizes order | [Section 27](#27-routing--optimization-architecture) |
| Anonymous rate limit | 3 plans/day (same as plan credits) | [7.3](#73-request-rate-limit--quota-architecture) |

---

## 25. Application Infrastructure Architecture (7.1–7.24)

Production-grade infrastructure design for CuVoy. All decisions assume **Render free tier**, **zero paid API usage**, and **3 plan credits/day**.

---

### 7.1 Complete Application Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                         │
│              Next.js 15 (Vercel — cuvoy.vercel.app)         │
│         Mapbox GL JS · TanStack Query · shadcn/ui           │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Render — FastAPI                         │
│   Planning Orchestrator · AI Gateway · Budget Enforcer      │
│   OR-Tools · H3/DBSCAN · Validation · Export generators     │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
       ▼              ▼              ▼
  Supabase        Upstash       External APIs
  (Auth, DB,      (Cache,       (Mapbox, OSM,
   Storage)        Sessions,     Open-Meteo,
                   Budgets)      Gemini, Groq…)
```

**Layers:**

| Layer | Platform | Responsibility |
|-------|----------|----------------|
| Presentation | Vercel (Next.js) | UI, map rendering, client-side PDF/`.ics`, SSE progress |
| Application | Render (FastAPI) | Pipeline orchestration, optimization, validation |
| Data | Supabase | Users, trips, saved itineraries, exports metadata |
| Cache | Upstash | API responses, POI datasets, sessions, budgets, dedup keys |
| External | Free-tier APIs | Places, routes, weather, LLM, holidays |

No permanent workers. No paid-tier fallbacks. No separate microservices in V1.

---

### 7.2 Background Job / Planning Queue Architecture

CuVoy does **not** run permanent background workers on Render free tier. Planning is handled as **on-demand, stage-based jobs** within request lifecycle.

```
User submits plan
        ↓
Create planning_job record (Supabase)
        ↓
Stage 1: Extract preferences        → cache checkpoint
Stage 2: Discover + enrich places   → cache checkpoint
Stage 3: Reduce candidates locally  → cache checkpoint
Stage 4: Cluster + Matrix           → cache checkpoint
Stage 5: Optimize + schedule        → cache checkpoint
Stage 6: Narrative + validate       → final result
        ↓
Update job status → SSE to frontend
```

| Property | Value |
|----------|-------|
| Queue type | In-request async stages (FastAPI `BackgroundTasks` + Upstash stage keys) |
| Permanent workers | None |
| Job persistence | `planning_jobs` table in Supabase |
| Resume on timeout | Read last Upstash checkpoint; continue from next stage |
| Priority | Single-user jobs only in V1; no multi-tenant queue |

If Render times out mid-plan, frontend polls job status. Backend resumes from last cached stage rather than restarting.

---

### 7.3 Request, Rate Limit & Quota Architecture

Three independent limit layers:

```
Layer 1 — User Plan Credits
   3 plans / day (IP or account)

Layer 2 — Per-Plan Internal API Budget
   LLM · Mapbox · OSM · Weather · Verification

Layer 3 — Provider Free-Tier Quotas
   Global daily/monthly caps per external API
```

**Layer 1 — Plan credits (user-facing):**

| User type | Key | Limit |
|-----------|-----|-------|
| Anonymous | IP + fingerprint hash | 3 plans/day |
| Logged in | Supabase user ID | 3 plans/day |

Stored in Upstash: `credits:{key}:{date}` → counter, TTL 24h.

**Layer 2 — Per-plan API budget (internal):**

| Sub-budget | Typical allocation | Exhausted behavior |
|------------|-------------------|-------------------|
| LLM | 4–6 calls/plan | Switch provider → deterministic narrative |
| Mapbox Search | 10–20 calls/plan | Use cached POI dataset |
| Mapbox Matrix | 1–3 calls/plan (post candidate reduction) | Use cached matrix or haversine estimate |
| OSM Overpass | 0–1 calls/plan (city batch) | Use cached POI dataset |
| Weather | 1 call/destination/day | Use cached forecast |
| Verification | 0–5 website fetches/plan | Skip verification; show warning |

**Layer 3 — Provider quotas (global):**

Tracked in Upstash: `quota:{provider}:{period}` → counter. When exhausted, provider disabled globally until period resets. Never escalate to paid tier.

**Regeneration budget:** Replanning consumes ~20–40% of a full plan's internal budget. Does not consume a user-facing plan credit if the trip was generated in the same session and within regeneration allowance (default: unlimited regens per plan, budget-capped).

---

### 7.4 Schema, Type & API Contract Architecture

Shared contracts between frontend, backend, and AI layers.

| Layer | Tool | Scope |
|-------|------|-------|
| Backend models | Pydantic v2 | Request/response, pipeline intermediates |
| Frontend types | TypeScript + Zod | Form validation, API response parsing |
| AI outputs | JSON Schema (in AI reference doc) | LLM structured outputs |
| API contract | OpenAPI 3.1 (auto-generated from FastAPI) | REST endpoints |

**Core API endpoints (V1):**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/plan` | Create new plan (consumes 1 credit) |
| POST | `/api/v1/plan/{id}/regenerate` | Partial replan |
| GET | `/api/v1/plan/{id}` | Fetch plan result |
| GET | `/api/v1/plan/{id}/status` | Poll job progress (SSE alternative) |
| GET | `/api/v1/plan/{id}/export/pdf` | Download PDF |
| GET | `/api/v1/plan/{id}/export/ics` | Download `cuvoy-trip.ics` |
| POST | `/api/v1/trips` | Save trip (auth required) |
| GET | `/api/v1/trips` | List saved trips (auth required) |

All times in responses include `timezone` (IANA ID) and `local_time` fields. Frontend never converts times without explicit user request.

Versioning: `/api/v1/` prefix. Breaking changes → `/api/v2/`.

---

### 7.5 Logging & Observability Architecture

Structured JSON logging from FastAPI. No paid observability tools in V1.

| Log field | Example |
|-----------|---------|
| `request_id` | UUID per plan request |
| `stage` | `candidate_reduction`, `matrix_fetch`, etc. |
| `provider` | `mapbox`, `gemini`, `overpass` |
| `budget_remaining` | `{ "llm": 3, "mapbox": 12 }` |
| `duration_ms` | Stage timing |
| `cache_hit` | true/false |

**Log destinations:**

| Environment | Destination |
|-------------|-------------|
| Development | stdout |
| Production | Render log stream (free) |

Log levels: `DEBUG` (dev only), `INFO` (stage completions), `WARN` (fallback triggered), `ERROR` (plan failure).

No PII in logs. Prompts logged as hashes only.

---

### 7.6 Error Monitoring Architecture

V1 uses **Sentry free tier** (5k events/month) for both Next.js and FastAPI.

| Error class | Handling |
|-------------|----------|
| Provider quota exhausted | WARN — not sent to Sentry; handled by budget enforcer |
| Validation failure | INFO — retry with repair pipeline |
| Unhandled exception | ERROR — Sentry + user-friendly message |
| Render timeout | WARN — job marked `resumable`; not Sentry unless repeated |

User-facing errors always include:
- What failed (plain language)
- Whether the user can retry
- Whether a plan credit was consumed (refund credit on server fault)

---

### 7.7 Complete Testing Architecture

| Layer | Tool | Scope |
|-------|------|-------|
| Backend unit | pytest | OR-Tools, H3/DBSCAN, crowd scoring, cost formulas, timezone |
| Backend integration | pytest + httpx | API endpoints, cache behavior, budget enforcement |
| Schema validation | pydantic + jsonschema | AI output parsing |
| Frontend unit | Vitest | Components, Zod schemas, timezone display |
| Frontend E2E | Playwright | Full plan flow, Trip Controls replan, export |
| Benchmark tests | pytest parametrized | 5 benchmark destinations (Bengaluru, Jaipur, Tokyo, Interlaken, Paris) |

**Critical test scenarios:**
- Candidate reduction reduces Matrix input size by ≥50%
- Plan credit enforced at 3/day
- Free-tier exhaustion triggers fallback, not paid call
- All itinerary times in destination-local timezone
- OSM city batch → no per-attraction Overpass calls
- Regeneration preserves locked stops

CI runs unit + integration on every PR. E2E on merge to main.

---

### 7.8 CI/CD Architecture

```
GitHub Push / PR
        ↓
GitHub Actions
        ├── Lint (ESLint, Ruff)
        ├── Type check (tsc, mypy)
        ├── Unit + integration tests
        └── (main only) E2E smoke test
        ↓
Merge to main
        ├── Vercel auto-deploy (frontend)
        └── Render auto-deploy (backend)
```

| Branch | Deploys to |
|--------|-----------|
| `main` | Production (cuvoy.vercel.app + Render prod) |
| PR branches | Vercel preview deployments |
| `develop` | Optional Render staging (if free tier allows) |

Secrets injected via GitHub Actions secrets → Vercel env vars; backend secrets managed in **Render dashboard**. Never committed to repo.

### Keep-Alive CRON Workflow (GitHub Actions)

Prevents Render spin-down during active hours and reduces Supabase free-tier auto-pause (7-day inactivity).

| Property | Value |
|----------|-------|
| Workflow file | `.github/workflows/keep-alive.yml` |
| Schedule | Every **10 minutes** (`*/10 * * * *`) |
| Target 1 | `GET {RENDER_SERVICE_URL}/health` — wakes Render web service |
| Target 2 | `GET {SUPABASE_URL}/rest/v1/` with `apikey: {SUPABASE_ANON_KEY}` — keeps Supabase project active |
| Secrets | `RENDER_HEALTH_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` in GitHub Actions secrets |
| Failure handling | Log warning only; do not fail the workflow on single ping miss |

```yaml
# .github/workflows/keep-alive.yml (reference implementation)
name: Keep-Alive Ping
on:
  schedule:
    - cron: '*/10 * * * *'
  workflow_dispatch:
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping Render health
        run: curl -fsS "${{ secrets.RENDER_HEALTH_URL }}" || echo "Render ping failed"
      - name: Ping Supabase REST
        run: |
          curl -fsS "${{ secrets.SUPABASE_URL }}/rest/v1/" \
            -H "apikey: ${{ secrets.SUPABASE_ANON_KEY }}" \
            -H "Authorization: Bearer ${{ secrets.SUPABASE_ANON_KEY }}" \
            || echo "Supabase ping failed"
```

> Keep-alive reduces cold starts but does not eliminate them (e.g. overnight gaps). Frontend cold-start UX remains mandatory.

---

### 7.9 Environment & Secrets Architecture

| Environment | Frontend | Backend | Database |
|-------------|----------|---------|----------|
| Local | `.env.local` | `.env` | Supabase local or dev project |
| Preview | Vercel preview env | Render staging | Supabase dev project |
| Production | Vercel production env | Render production | Supabase production |

**Secret categories:**

| Category | Storage | Access |
|----------|---------|--------|
| Public (Mapbox token, Supabase anon) | Vercel `NEXT_PUBLIC_*` | Client + server |
| Private (service keys, LLM keys) | **Render dashboard** → Environment | Server only |
| Auth secrets | Supabase dashboard | Supabase only |

`.env.example` committed to repo with placeholder values. Actual secrets never in git.

Rotation: manual in V1. Document rotation procedure in README.

---

### 7.10 OR-Tools Runtime & Hosting Architecture

OR-Tools is the **itinerary optimization engine** — it determines visit order from a Mapbox-provided travel-time matrix. It does **not** compute routes.

| Property | Value |
|----------|-------|
| Role | Optimal visit order given Mapbox Matrix travel times |
| Routing | Mapbox Matrix + Directions (separate from OR-Tools) |
| Solver | OR-Tools routing (TSP/VRP variant) |
| Hosting | In-process within FastAPI on Render (512 MB RAM limit) |
| Input size | Post candidate-reduction set (typically 8–20 stops/day) |
| Timeout | 10 seconds max per optimization call |
| Fallback | Greedy nearest-neighbor if OR-Tools times out |

```
Reduced candidates (≤20 per day)
        ↓
Mapbox Matrix → travel-time matrix
        ↓
OR-Tools (in-process, ≤10s timeout) → optimal visit order
        ↓
Mapbox Directions → route geometry per leg
        ↓
(fallback) Greedy nearest-neighbor order + Mapbox Directions
```

---

### 7.11 Timezone Architecture

All itinerary scheduling uses **destination-local time**.

```
Destination coordinates
        ↓
timezonefinder → IANA timezone ID (e.g. Asia/Tokyo)
        ↓
Store on trip record: trip.timezone
        ↓
All schedule times rendered in local time
        ↓
.ics export includes TZID property
        ↓
PDF shows local time + timezone abbreviation
```

| Component | Timezone handling |
|-----------|-------------------|
| Day start/end | Local (e.g. 09:00 JST) |
| Meal windows | Local |
| Opening hours | Local (from OSM `opening_hours` tag) |
| Sunrise/sunset | Local (Sunrise-Sunset.org with lat/lon) |
| Multi-city trips | Each day uses that city's local timezone |
| Frontend display | Show local time; optional toggle to show user's home timezone |

**Multi-city example:** Day 1–3 Tokyo (JST), Day 4 travel, Day 5–7 Kyoto (JST). Travel day times use departure city timezone until arrival, then switch.

No TimeZoneDB API. Uses `timezonefinder` (Python) + `zoneinfo` stdlib.

---

### 7.12 Persistence & Cache Architecture

Two-tier storage: Supabase (durable) + Upstash (ephemeral/fast).

```
┌─────────────────────────────────────────────┐
│                  Supabase                   │
│  users · trips · planning_jobs · exports    │
│  Durable, relational, auth-linked           │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│                  Upstash                    │
│  API cache · POI datasets · sessions        │
│  plan credits · quotas · stage checkpoints  │
│  computation cache · dedup keys             │
│  Ephemeral, fast, TTL-based                 │
└─────────────────────────────────────────────┘
```

| Data | Supabase | Upstash |
|------|----------|---------|
| User accounts | Yes | No |
| Saved trips | Yes | No |
| Active plan session | Job record | Full pipeline state |
| API responses | No | Yes (TTL-based) |
| Plan credits counter | No | Yes (24h TTL) |
| Provider quota counters | No | Yes (period TTL) |
| OR-Tools results | No | Yes (session TTL) |

Write pattern: pipeline writes checkpoints to Upstash after each stage. Final validated result written to Supabase (if user saves) and returned to frontend.

---

### 7.13 Real-Time Progress & Replanning Architecture

Frontend receives planning progress via **Server-Sent Events (SSE)**.

```
Frontend                    Backend
   │                           │
   ├── POST /plan ────────────►│
   │                           ├── Stage 1…N
   │◄── SSE: {stage, pct} ─────┤
   │◄── SSE: {stage, pct} ─────┤
   │◄── SSE: {complete, data} ─┤
   │                           │
   ├── POST /regenerate ──────►│ (reuses cached stages 1–3)
   │◄── SSE: {stage, pct} ─────┤
   │◄── SSE: {complete, data} ─┤
```

| Event | Payload |
|-------|---------|
| `stage_start` | `{ stage: "clustering", progress: 40 }` |
| `stage_complete` | `{ stage: "clustering", progress: 55 }` |
| `plan_complete` | `{ plan_id, itinerary }` |
| `plan_error` | `{ error, recoverable, credit_refunded }` |

**Replanning fast path:**

```
Trip Controls change detected
        ↓
Identify changed constraint (e.g. lunch time, max transit)
        ↓
Load cached: preferences, candidates, POI dataset, matrix
        ↓
Re-run only affected stages (typically: optimize → schedule → narrative)
        ↓
SSE progress (typically <5 seconds)
```

Locked stops passed as hard constraints to OR-Tools. Skipped stops removed from candidate set.

---

### 7.14 Idempotency & Request Deduplication

Prevents duplicate API spend from retries, double-clicks, or network failures.

| Mechanism | Implementation |
|-----------|----------------|
| Idempotency key | Client sends `Idempotency-Key: {uuid}` header on POST `/plan` |
| Dedup window | Upstash: `idempotency:{key}` → cached response, TTL 24h |
| Exact request hash | SHA-256 of normalized prompt + constraints → cache AI/plan results (7 days) |
| Credit protection | Credit consumed once per idempotency key; retries return cached result |

```
POST /plan (Idempotency-Key: abc-123)
        ↓
Check Upstash idempotency:abc-123
        ↓ (hit)  → return cached plan, no new credit
        ↓ (miss) → consume credit, run pipeline, store result
```

Regeneration requests deduplicated by `{plan_id}:{change_hash}`.

---

### 7.15 Share & Export Architecture

| Export | Method | Generated by |
|--------|--------|-------------|
| PDF | Client-side canvas + `@react-pdf/renderer` or html2canvas | Frontend (map snapshot from Mapbox canvas) |
| `.ics` | Server-generated `cuvoy-trip.ics` | Backend (FastAPI) |
| Share link | Supabase stored trip + UUID slug | Backend + Supabase |

**PDF contents:**
- CuVoy logo (corner)
- Day-by-day text itinerary (local times, costs, notes)
- Map route snapshot with average travel times labeled along route
- AI disclaimer footer

**`.ics` contents:**
- Each stop = `VEVENT` with `DTSTART`/`DTEND` in destination timezone (`TZID`)
- Location = place name + coordinates
- Description = explainability snippet + cost estimate

**Share flow (auth required):**
```
Save trip → Supabase
        ↓
Generate share slug: cuvoy.vercel.app/trip/{slug}
        ↓
Read-only view for recipients
```

---

### 7.16 Frontend Production Architecture

| Concern | Decision |
|---------|----------|
| Rendering | Next.js App Router, RSC for static shell, client components for map/interactivity |
| Map | Mapbox GL JS (client-only, dynamic import) |
| State | TanStack Query for server state; React context for Trip Controls |
| Auth | Supabase Auth JS client |
| Theming | next-themes (light/dark), CSS variables, no gradients |
| Bundle | Mapbox loaded lazily; code-split by route |
| SEO | Static landing page; plan pages `noindex` |
| Error boundaries | Per-panel (map, itinerary, controls) — one panel failure doesn't crash page |
| Cold start UX | *"Waking up the AI planner…"* during Render 45–60s wake; ≥90s timeout on first request after idle |

Frontend never calls external APIs directly (except Mapbox GL for rendering). All planning logic goes through FastAPI.

---

### 7.17 Backend Production Architecture

| Concern | Decision |
|---------|----------|
| Framework | FastAPI (async) |
| Structure | Modular services: `planner/`, `ai_gateway/`, `budget/`, `cache/`, `export/` |
| Concurrency | Async I/O for API calls; OR-Tools in thread pool executor |
| Health check | `GET /health` → `{ status, cache, db }` |
| CORS | `cuvoy.vercel.app` + preview URLs only |
| Request timeout | Stage checkpointing for long plans; client allows ≥90s on cold-start first request |
| Graceful shutdown | Finish current stage, write checkpoint, return resumable status |

No Celery, no Redis server (Upstash REST only), no separate worker dyno.

---

### 7.18 Deployment Architecture

```
GitHub (main)
    ├── Vercel ──► cuvoy.vercel.app (frontend, Mumbai edge)
    └── Render ──► cuvoy-api (backend, Mumbai primary)
            │
            ├── Supabase (Mumbai-compatible region)
            └── Upstash (Mumbai region)
```

| Service | Region | Fallback |
|---------|--------|----------|
| Vercel | Mumbai (bom1) | Auto CDN |
| Render | Mumbai | Singapore |
| Supabase | Closest available | — |
| Upstash | Mumbai | Singapore |

Domain: `cuvoy.vercel.app` (V1). Custom domain deferred.

Render: single web service, single instance, **512 MB RAM**, spins down after **15 minutes** of inactivity.

**Cold start:** first request after sleep may take **45–60 seconds** — frontend shows *"Waking up the AI planner…"*. Keep-alive CRON (every 10 min) reduces daytime sleep; see [7.8](#78-cicd-architecture).

---

### 7.19 Security Architecture

| Threat | Mitigation |
|--------|------------|
| API key exposure | Private keys server-side only; Mapbox token restricted by URL in Mapbox dashboard |
| Abuse / bot plans | 3 credits/day + IP rate limit + idempotency keys |
| SQL injection | Supabase parameterized queries + RLS policies |
| Auth bypass | Supabase JWT validation on protected endpoints |
| CORS abuse | Whitelist Vercel origins only |
| Prompt injection | LLM outputs validated against JSON schema; never executed |
| SSRF (website verification) | Allowlist HTTP fetch to known domains only; timeout 5s |
| Data deletion | GDPR delete endpoint purges Supabase + invalidates Upstash session keys |

Supabase Row Level Security: users can only read/write their own trips.

---

### 7.20 Performance & Resource Management

| Optimization | Impact |
|-------------|--------|
| Candidate reduction before Matrix | Reduces Mapbox Matrix cost by 50–80% |
| OSM city batch + cache | Reduces Overpass calls from N to 1 per city |
| Upstash cache hits | Eliminates redundant API calls across users |
| Stage checkpointing | Avoids full re-computation on timeout/retry |
| Regeneration fast path | Reuses cached stages; typical replan <5s |
| Frontend lazy loading | Mapbox GL loaded on demand |
| OR-Tools timeout | 10s cap prevents CPU exhaustion within 512 MB RAM budget |

**Memory budget (512 MB):** OR-Tools matrices, GTFS artifacts, and in-process caches must stay bounded. Preprocess GTFS offline; never full Pandas load at runtime.

**Target performance (V1):**

| Metric | Target |
|--------|--------|
| New plan generation | ≤30 seconds (backend warm) |
| Regeneration (Trip Controls) | ≤5 seconds |
| PDF export | ≤3 seconds (client-side) |
| `.ics` download | ≤1 second |
| Cold start (Render spin-down) | **45–60 seconds** — show *"Waking up the AI planner…"* |
| Backend warm after keep-alive | Normal pipeline progress via SSE |

---

### 7.21 Failure Injection & Reliability Testing

Pre-production reliability tests (run manually before launch, automated where possible):

| Test | Expected behavior |
|------|-------------------|
| Mapbox quota exhausted | Use cached matrix; haversine fallback for uncached pairs |
| Gemini quota exhausted | Failover to Groq → OpenRouter → deterministic narrative |
| Overpass timeout | Use cached POI dataset; proceed with Mapbox-only metadata |
| Render timeout at stage 4 | Job marked `resumable`; resume from stage 5 on retry |
| Render cold start | Frontend shows wake UI; ≥90s client timeout on first request |
| Invalid LLM JSON | Schema repair → retry once → deterministic fallback |
| Double-click plan button | Idempotency key prevents duplicate credit + API spend |
| 4th plan in one day | HTTP 429 with "3 plans/day limit reached" message |
| Destination with no GTFS | Transit fare shows "Fare unavailable" |

Benchmark destinations (section 22) used as reliability test fixtures.

---

### 7.22 Complete API Lifecycle Architecture

End-to-end lifecycle for a single plan request:

```
1. REQUEST INTAKE
   Client → POST /api/v1/plan
   Validate schema · Check plan credits · Check idempotency key

2. BUDGET ALLOCATION
   Create internal budget envelope (LLM, Mapbox, OSM, Weather, Verification)
   Deduct 1 user plan credit

3. PREFERENCE EXTRACTION
   LLM (Gemini) → structured JSON
   Resolve destination timezone

4. PLACE DISCOVERY
   Mapbox Search → raw candidates
   OSM city batch (cache-first) → enrich
   Official website verification (budget-capped)

5. LOCAL PROCESSING (zero API cost)
   Filter closed/out-of-season
   Candidate reduction (≥50% shrink)
   H3 index → DBSCAN cluster
   Crowd confidence scoring

6. ROUTING & OPTIMIZATION
   Mapbox Matrix (reduced set) → travel-time matrix
   OR-Tools → optimal visit order
   Mapbox Directions → route geometry + leg details
   Schedule builder (local times, meals, breaks, travel days)

7. ENRICHMENT
   Cost calculation (GTFS/formulas)
   Weather check (cache-first)
   LLM narrative + explainability + packing list

8. VALIDATION
   Cross-schema validation
   Conflict detection (hours, reservations)
   Confidence scoring

9. DELIVERY
   Cache result (Upstash + dedup key)
   SSE complete event → frontend
   Render map + itinerary

10. LIFECYCLE AFTER DELIVERY
    User edits Trip Controls → regeneration (fast path, fractional budget)
    User saves → Supabase persist
    User exports → PDF (client) / .ics (server)
    Session expires → Upstash TTL cleanup
```

---

### 7.23 Complete Production Readiness Matrix

| Area | Requirement | Status |
|------|-------------|--------|
| Auth | Email + Google via Supabase | Specified |
| Plan limits | 3 credits/day enforced | Specified |
| API budget | Per-plan internal envelope | Specified |
| Free-tier guard | Never auto-upgrade to paid | Specified |
| Timezone | Destination-local times | Specified |
| Caching | Upstash multi-layer | Specified |
| OSM batching | City/region, not per-attraction | Specified |
| Candidate reduction | Before Matrix API | Specified |
| Error monitoring | Sentry free tier | Specified |
| CI/CD | GitHub Actions → Vercel + Render | Specified |
| Testing | pytest + Playwright + benchmarks | Specified |
| Legal | Privacy policy, GDPR, AI disclaimer | Specified |
| Export | PDF + `.ics` | Specified |
| Deployment | Vercel + Render + Supabase + Upstash | Specified |
| Cold start | "Waking up the AI planner…" UX; 45–60s; keep-alive CRON | Specified |
| Memory (512 MB) | OR-Tools bounded; GTFS preprocessed offline | Specified |
| Share | Auth-required share links | Specified |
| GTFS fare registry | On-demand fetch, cache 30 days, graceful degradation | Specified |
| PDF render method | Client-side canvas (preferred) | Specified |

---

### 7.24 Complete Application Infrastructure Summary

Consolidated view of all infrastructure decisions:

```
┌─────────────────────────────────────────────────────────────────┐
│                         CuVoy V1                                │
├─────────────────────────────────────────────────────────────────┤
│  Users: Anonymous (3 plans/day) · Auth to save (Email + Google) │
│  Times: Destination-local (timezonefinder + zoneinfo)           │
│  Credits: 3/day · Regen = fractional internal budget            │
│  APIs: Free tier only · Never auto-pay · Cache-first            │
├─────────────────────────────────────────────────────────────────┤
│  Frontend   │ Vercel · Next.js 15 · Mapbox GL · TanStack Query │
│  Backend    │ Render · FastAPI · OR-Tools · No workers         │
│  Database   │ Supabase · Auth · RLS · Trip persistence          │
│  Cache      │ Upstash · API cache · POI datasets · Budgets      │
│  AI         │ Gemini → Groq → OpenRouter → Deterministic        │
│  Monitoring │ Sentry free · Structured JSON logs                │
│  CI/CD      │ GitHub Actions → Vercel + Render auto-deploy     │
│  Export     │ PDF (client) · .ics (server) · Share links        │
├─────────────────────────────────────────────────────────────────┤
│  Key optimizations:                                             │
│  · OSM city batch (not per-attraction)                          │
│  · Candidate reduction before Matrix                              │
│  · Stage checkpointing (Render timeout recovery)               │
│  · Keep-alive CRON (Render + Supabase, every 10 min)          │
│  · Cold-start UX ("Waking up the AI planner…")                 │
│  · 512 MB RAM discipline (OR-Tools + GTFS)                    │
│  · Idempotency keys (no duplicate spend)                        │
│  · Regeneration fast path (cached stages 1–3)                   │
└─────────────────────────────────────────────────────────────────┘
```

This section closes the infrastructure specification. Implementation should follow sections 7.1–7.24 alongside the AI architecture reference and product rules defined in sections 1–24.

---

## 26. Changelog

| Date | Change |
|------|--------|
| 2026-08-03 | Initial spec from project kickoff |
| 2026-08-08 | Full CuVoy branding, global scope, V1 feature set, caching, place data, crowd confidence, pricing, transport presets, Trip Controls UX, deployment, legal, API checklist |
| 2026-08-11 | Backend compute minimization; Email + Google auth; `.ics` export; group planning UX + scoring modes; GTFS fare strategy; PDF layout; reservation contact info rules |
| 2026-08-12 | Destination-local times; 3 plan credits/day; per-plan API budget; OSM city batching; candidate reduction before Matrix; free-tier hard stop; Application Infrastructure Architecture (7.1–7.24) |
| 2026-08-12 | Transport cost toggle (opt-in); three-tier cost labels (Verified / Estimated / Unavailable); GTFS graceful degradation |
| 2026-08-13 | Mapbox routing vs OR-Tools optimization; Open-Meteo Historical API; resolved open items; supplementary architecture (sections 27–34) |
| 2026-08-14 | **Backend host: Railway → Render**; 15 min spin-down; 45–60s cold-start UX; keep-alive GitHub Actions CRON; 512 MB RAM constraints; Render dashboard env vars |

---

## 27. Routing & Optimization Architecture

### Engine Responsibilities

| Component | Role | Implements routing? |
|-----------|------|---------------------|
| **Mapbox Matrix API** | Pairwise travel times and distances between stops | Yes (routing service) |
| **Mapbox Directions API** | Route geometry, turn-by-turn leg details, polylines | Yes (routing service) |
| **OR-Tools** | Optimal visit order given a travel-time matrix | No — optimization only |
| **CuVoy backend** | Orchestrates the above; never computes road networks | No |

CuVoy does **not** implement road-network routing from scratch.

### Standard Flow

```
Places (reduced candidate set)
        ↓
Mapbox Matrix API
        ↓
Travel-time / distance matrix
        ↓
OR-Tools
        ↓
Optimal visit order
        ↓
Mapbox Directions API
        ↓
Actual route geometry + leg details
```

### Progressive Problem Reduction

```
~500 OSM places → ~100 relevant → ~40 strong → 4–6 clusters
        ↓
8–15 places/cluster → Mapbox Matrix → OR-Tools → 4–6 stops/day
        ↓
Mapbox Directions → Final route on map
```

Matrix provides travel-time **costs** to the optimizer. Directions provides **geometry** only after OR-Tools determines order.

---

## 28. GTFS Feed Registry

CuVoy maintains a registry of public-transit GTFS feeds for benchmark cities and on-demand discovery for other cities.

### Registry Schema

| Field | Description |
|-------|-------------|
| `city` | Benchmark or served city |
| `country` | Country |
| `agency` | Transit agency / provider |
| `feed_url` | Official GTFS feed URL |
| `feed_type` | Static GTFS / GTFS-Realtime (if applicable) |
| `schedule_available` | Whether schedule data is usable |
| `fare_available` | Whether usable fare data is present |
| `last_updated` | Last successful feed refresh |
| `status` | `active` / `unavailable` / `outdated` |
| `cache_ttl` | How long cached feed data remains valid |

### Feed Selection Rules

1. Prefer official transit-agency GTFS feeds.
2. If unavailable, use a trusted public GTFS aggregator where permitted.
3. Never use LLM-generated transit schedules, routes, or fares as authoritative data.
4. If no reliable GTFS feed exists, CuVoy still plans the trip using walk/drive/taxi — but must not claim unsupported transit details.
5. GTFS data is downloaded and cached (30 days), not fetched on every itinerary request.
6. Fare data used for cost estimation only when `fare_available = true`; otherwise **Cost unavailable**.

### Implementation Note

> The actual city/agency/feed URLs will be finalized during implementation after verifying current feed availability. Do not hardcode unverified feed URLs in the architecture document. A separate concrete registry (e.g. `Bengaluru → Agency → URL → fares: yes/no`) will be created after a verification pass.

### GTFS Runtime Constraints

- Never download and fully parse large GTFS feeds during user-facing generation.
- Preprocess benchmark-city feeds offline; store compact city-specific artifacts in Supabase Storage or bundled deployment assets.
- Never load an entire large GTFS CSV into Pandas at runtime on Render free tier.

---

## 29. Validation & Data Processing

### 29.1 LLM JSON Cleaning & Parsing Layer

LLM responses must **never** pass directly to Pydantic. A deterministic cleaning layer sits between raw LLM output and schema validation.

```
LLM Response → Extract JSON → Remove fences → Normalize → json.loads()
     → Pydantic validation → Semantic validation → Final itinerary
```

**Cleaner may:** remove Markdown wrappers, strip surrounding prose, fix trailing commas, extract first valid JSON object.

**Cleaner must not:** invent missing fields or repair semantics.

**Failure:** Attempt 1 → clean → parse → FAIL → retry/regenerate → deterministic fallback. Never send malformed JSON to frontend.

### 29.2 Weather Horizon & Historical Climate Fallback

CuVoy distinguishes **forecast weather** from **historical climate estimates**. Never call historical climate a "forecast."

| Tier | Source | `is_forecast` | Confidence |
|------|--------|---------------|------------|
| Live Forecast | Open-Meteo Forecast API | `true` | High |
| Historical Climate | Open-Meteo Historical Weather API (ERA5/ERA5-Land, global back to 1940) | `false` | Low/Moderate |
| Unavailable | Neither source | — | None |

- Use **climatological baselines** (monthly averages), not one arbitrary past day.
- Forecast horizon checked dynamically.
- Live forecast → strong planning influence; historical climate → soft preference only.
- Weather unavailability must not break itinerary generation.

### 29.3 Failure / Fallback Matrix (supplementary)

| Failure | Primary | Fallback | Final behavior |
|---------|---------|----------|----------------|
| Markdown-wrapped JSON | JSON cleaner | — | Parse cleaned JSON |
| Invalid JSON | Cleaner/parser | LLM regeneration | Deterministic failure |
| Forecast unavailable | Open-Meteo Forecast | Historical climate API | Continue, lower confidence |
| Weather API failure | Open-Meteo | Cached weather | Continue if cache hit |

---

## 30. AI Gateway — Rate Limit & Recovery

All LLM requests pass through centralized **AI Gateway** with rate limiter, queue, concurrency control, provider quota state, retry/backoff, failover, and circuit breaker. `paid_fallback = NEVER`.

Key rules: configurable RPM/TPM/RPD per provider; max 3 retries with exponential backoff + jitter; respect `Retry-After`; retry failed stage only (not entire pipeline); user sees "CuVoy is handling high demand…" not raw 429 errors.

See [Section 21](#21-ai-architecture-summary) and [`docs/AI_ARCHITECTURE_REFERENCE.md`](docs/AI_ARCHITECTURE_REFERENCE.md) for full AI Gateway spec.

---

## 31. OSM Cache & Payload Architecture

Raw Overpass data must never go directly to Upstash or the LLM. Pipeline: Overpass → filter → normalize → deduplicate → size check → compress → Upstash.

**Canonical Place schema:** `id`, `name`, `lat`, `lng`, `category`, `opening_hours` (optional), `source`.

Partition caches by city + category. Configurable `MAX_CACHE_PAYLOAD`; partition if exceeded. Cache failure never breaks generation.

---

## 32. Adaptive DBSCAN Clustering

Adaptive epsilon from geographic extent + point density (not globally fixed). Cluster within destinations only. Noise points retained. Re-cluster if too large. Failure → skip clustering → OR-Tools directly.

---

## 33. Matrix API Constraints

Never send full candidate set to Matrix. Pre-filter → cluster → rank → Matrix (reduced set) → OR-Tools → Directions. Matrix failures use labeled approximate estimates.

---

## 34. Platform Reliability & Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Vercel serverless timeout | Long generation on Render only; async job_id + poll/SSE |
| Render spin-down (15 min idle) | Keep-alive CRON every 10 min; cold-start UX ("Waking up the AI planner…") |
| Render memory (512 MB) | Preprocess GTFS offline; bounded OR-Tools input; no full Pandas GTFS load |
| Supabase connection exhaustion | Use Supabase API client, not direct PostgreSQL pools |
| Supabase auto-pause (7-day inactivity) | Keep-alive CRON pings Supabase REST API; health checks + retry/backoff |
| Mapbox–OSM identity mismatch | Geospatial proximity + category match; never LLM matching |
| Upstash command quota | Adaptive polling, pipelining/MGET, compact state |
| Upstash REST latency | Batch Redis operations; keep active state in memory |
| Timezone / DST | IANA IDs, timezone-aware datetimes, explicit TZID in `.ics` |

**Core timezone rule:** Local timezone-aware datetimes define the itinerary; UTC for absolute calculations; display conversion at output layer only.
