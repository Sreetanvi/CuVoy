# CuVoy — Curating One's Voyage

Global AI travel planner. Natural-language request → feasible, costed, explainable day-by-day itinerary with an interactive map.

**Source of truth:** [`PROJECT_SPEC.md`](PROJECT_SPEC.md). Prompts, JSON schemas, and model-routing detail live in [`docs/AI_ARCHITECTURE_REFERENCE.md`](docs/AI_ARCHITECTURE_REFERENCE.md) — use that only when the spec is silent.

LLMs reason. Mapbox routes. OR-Tools optimizes. Deterministic code validates. The LLM never invents places, coordinates, hours, travel times, or factual prices.

## Stack (V1)

| Layer | Platform |
|-------|----------|
| Frontend | Next.js 15 · Vercel (`cuvoy.vercel.app`, Mumbai `bom1`) |
| Backend | FastAPI · **Render** free web service (Singapore — closest region to Mumbai) |
| Database / Auth | Supabase (Email + Google) |
| Cache | Upstash Redis |
| Maps | Mapbox |
| AI | Gemini free → Groq free → OpenRouter free → deterministic fallback |

No Railway. No paid-tier auto-upgrade. No permanent workers. 3 plan credits per day.

## Repository layout

```
backend/                  FastAPI (Part 1+)
frontend/                 Next.js App Router (Part 9+)
packages/contracts/       Shared Pydantic v2 + Zod contracts (this part)
docs/                     Spec companion docs
.github/workflows/        CI + keep-alive CRON (every 10 min)
render.yaml               Render Blueprint
PROJECT_SPEC.md           Product + infrastructure spec
```

## Local environment

1. Copy placeholders (do not commit filled files):

   ```text
   backend/.env.example   → backend/.env
   frontend/.env.example  → frontend/.env.local
   ```

2. Paste keys when you have them (chat is fine). Use the **exact names** in [Section 23](PROJECT_SPEC.md#23-api-keys-checklist).

3. `SUPABASE_URL` on the backend is the same project URL as `NEXT_PUBLIC_SUPABASE_URL`. The spec lists the public name; the Python client still needs the URL server-side.

### Variable names

**Frontend (Vercel / `.env.local`)**

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN`
- `NEXT_PUBLIC_FASTAPI_URL`

**Backend (Render dashboard / `.env`)**

- `MAPBOX_ACCESS_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `OPENROUTER_API_KEY`
- `OPENTRIPMAP_API_KEY`
- `GEONAMES_USERNAME`
- `FASTAPI_SECRET_KEY`
- `CORS_ORIGINS`

Optional: `SENTRY_DSN`. GitHub Actions keep-alive: `RENDER_HEALTH_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`.

### Key rotation (V1, manual)

1. Create a new key at the provider.
2. Update **local** `.env` / `.env.local`.
3. Update **Vercel** (public vars) or **Render dashboard** (private vars).
4. Revoke the old key at the provider.
5. Never put values in markdown, git, or CI logs.

## Run locally

Backend (Part 1):

```text
cd backend
pip install -r requirements.txt
pip install pytest ruff
uvicorn app.main:app --reload --port 8000
```

`GET http://localhost:8000/health` returns `{ status, cache, db }` (HTTP 200 even if cache/db are unavailable). OpenAPI: `http://localhost:8000/docs`.

Keys live in gitignored `backend/.env` and `frontend/.env.local`. GitHub Actions keep-alive should use the Supabase **project origin** (no `/rest/v1`) because the workflow appends that path.

Frontend (Part 9 shell):

```text
cd frontend
npm install
npm run dev
```

The app depends on `@cuvoy/contracts` via `file:../packages/contracts/typescript`. You do **not** need to install from the repo root. If the module is missing, from `frontend` run `npm install` again so `node_modules/@cuvoy/contracts` is linked.

`http://localhost:3000` — cinematic landing, then the planner: generate a trip, watch SSE progress, map + itinerary, and Trip Controls regenerate. Map rendering needs `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN`.

Legal pages: `/privacy` (collection, use, GDPR delete) and `/disclaimer` (AI + cost-label copy). The planner footer repeats the AI disclaimer.

## Tests

Backend (from `backend/`):

```text
pip install -r requirements.txt
pip install pytest pytest-asyncio ruff
ruff check app tests
pytest
```

`pytest` runs unit, integration (credits, idempotency, free-tier stop), and the five benchmark destinations (Bengaluru, Jaipur, Tokyo, Interlaken, Paris).

Frontend (from `frontend/`):

```text
npm install
npm run typecheck
npm run lint
npm test
npx playwright install chromium
npm run e2e
```

CI (`.github/workflows/ci.yml`) runs lint, typecheck, and unit/integration on every PR. Playwright E2E runs on push to `main`. Keep-alive stays in `.github/workflows/keep-alive.yml`.

Contracts:

```text
cd packages/contracts/python && pip install -e ".[dev]" && pytest
cd packages/contracts/typescript && npm install && npx tsc --noEmit
```

## Deploy

- **Frontend:** Vercel project, Root Directory `frontend`, region `bom1`. See `frontend/vercel.json`.
- **Backend:** Render Blueprint `render.yaml` — free plan, 512 MB, `/health`, spins down after 15 minutes idle. First request after sleep can take 45–60s; UI must show “Waking up the AI planner…”.
- **Keep-alive:** `.github/workflows/keep-alive.yml` pings Render + Supabase every 10 minutes.

## API prefix

All planner endpoints are `/api/v1/` (spec §7.4). OpenAPI 3.1 is generated from FastAPI in Part 1 — do not hand-maintain `openapi.json` here.
