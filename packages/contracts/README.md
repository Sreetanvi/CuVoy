# @cuvoy/contracts

Shared V1 types for CuVoy. **Pydantic v2** (backend) and **Zod** (frontend) must stay in lockstep.

Source of truth for *what* exists: [`PROJECT_SPEC.md`](../../PROJECT_SPEC.md) §4, §7.4, §9–10, §18, §31.  
[`docs/AI_ARCHITECTURE_REFERENCE.md`](../../docs/AI_ARCHITECTURE_REFERENCE.md) is used only for field-level gaps.

JSON field names are **snake_case** on the wire. All schedule times include `timezone` (IANA) and `local_time`; the frontend must not convert times unless the user asks.

OpenAPI 3.1 is auto-generated from FastAPI in Part 1 (`/openapi.json`). This package is the hand-written contract the API will implement.

## Layout

| Path | Role |
|------|------|
| `python/` | `cuvoy-contracts` — Pydantic models |
| `typescript/` | `@cuvoy/contracts` — Zod schemas |

When you change a field, update **both** packages and the tests in `python/tests`.
