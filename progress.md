# ATLAS Project Progress

**Last reviewed:** 9 September 2026
**Review method:** Read the project PRDs and completion reports, inspected every tracked source and scaffold directory, reviewed the current working tree, and ran local build, compile, import, health-check, and test-discovery commands.

## Overall status

ATLAS is a **functional travel-planning prototype, approximately 65% complete against the Version 1 PRD**. Its strongest areas are the polished React interface, email/password authentication, PostgreSQL persistence, a Gemini-backed single-turn travel assistant, and a structured, authenticated trip-generation endpoint with concurrent sub-agent context and fallback handling. The broader multi-agent planning and decision pipeline remains future work.

The repository also contains **uncommitted Google OAuth work in progress**. The source, migration, backend routes, frontend callback page, and configuration changes exist. The migration has been applied and its database schema verified; the OAuth flow itself has not yet been integration-tested against Google.

## Verified implementation

### Documentation and product definition

- `docs/PRD Files/` contains the project overview, PRD, information architecture, UI/UX guidance, design system, component library, and detailed specifications for public, planning, assistant, community, booking, profile, and system pages.
- The defined product is an AI-assisted travel planning platform, not only a booking UI: it calls for coordinated transport, hotel, food, activity, weather, maps, review, budget, and constraint agents.
- `README.md`, `PHASE_2A_COMPLETION_REPORT.md`, and `PROJECT_COMPLETION_STATUS.md` document prior phases. This file reflects the current source tree and verification results.

### Frontend

- The Vite/React/TypeScript application contains all 15 planned UI pages: home, about, authentication, dashboard, exploration, activities, food, planner, itinerary, assistant, trips, bookings, saved places, Lost & Found, profile, and settings.
- Shared layout, card, modal, form, planner, itinerary, Markdown, and booking-flow components are implemented, together with local destination imagery and catalogue data.
- The production bundle builds successfully with `npx.cmd vite build` on 9 September 2026. The generated JavaScript bundle is about 625 kB before gzip and triggers Vite's chunk-size warning.
- Email/password authentication is connected to the FastAPI backend. Persisted trips and saved places are loaded for authenticated users.
- Discovery, activity, restaurant, booking, Lost & Found, map, weather, and planner experiences still rely substantially on local mock data and rule-based plan generation.
- Google OAuth UI work is present but uncommitted: a Google login button, `/auth/callback` route, token session initialization, and backend auth URL helper have been added. The strict TypeScript check and production build pass.

### Backend, data, and AI

- The active FastAPI application is `backend/app/main.py`; it configures CORS, session middleware, health checks, authentication, trips, saved places, and chat routes.
- `GET /health` was verified locally with FastAPI's test client and returned `200 {"status":"ok"}`.
- JWT authentication, bcrypt password hashing, registration, login, and `/api/auth/me` are implemented.
- SQLAlchemy models, Pydantic schemas, Alembic migrations, and authenticated CRUD routes exist for users, trips, itinerary days, and saved places. Ownership is enforced in the route queries.
- The Gemini service exposes a single-turn `POST /api/chat` travel-assistant endpoint. It reads its API key from backend environment configuration and contains a system prompt, but does not retain conversation history or invoke a real agent pipeline.
- A preliminary `PlannerAgent` class calls route, hotel, food, and weather agents in parallel, but those agent files only return mock/stub data and the planner is exposed through the separate legacy `backend/main.py` entry point rather than the active `app` application.
- Google OAuth backend work is present but uncommitted: Authlib configuration, session middleware, Google redirect/callback routes, a `google_id` column migration, and optional password hashes for OAuth-only users. Alembic reports the database is at `add_google_oauth (head)`; schema inspection confirms the nullable, uniquely indexed `google_id` column and nullable `password_hash` column.
- `POST /api/trips/generate` accepts authenticated structured planning input, validates Gemini JSON against Pydantic schemas, and persists the generated trip and every itinerary day in a single database transaction.
- The obsolete standalone `backend/main.py` entry point and duplicate empty backend scaffolds have been removed; `backend/app/main.py` is the sole application entry point.
- JWT startup validation now requires `JWT_SECRET_KEY` to be at least 32 bytes. The local development secret was rotated to a 64-byte value without exposing it.
- AI endpoints are rate limited in-process: authenticated trip generation is limited to 5 requests per minute per user, and chat is limited to 20 requests per minute per client IP.
- The planner concurrently runs route, hotel, food, and weather agents with a five-second timeout per agent. Route and weather connectors use timeout-protected circuit breakers; all agent and integration failures produce marked fallback context rather than aborting trip persistence.
- Structured Gemini generation retries transient or malformed responses up to two times. Configuration, validation, and provider failures return explicit `503`, `422`, and `502` responses instead of unhandled server errors.

## Verification results

| Check | Result | Notes |
| --- | --- | --- |
| Frontend production build | Passed | `npx.cmd vite build` completed successfully. |
| Frontend strict type check | Passed | `npx.cmd tsc --noEmit` completes with zero diagnostics after itinerary, environment, Markdown, button, and import fixes. |
| Backend Python compilation | Passed | `python -m compileall` completed without errors. |
| Backend application import | Passed | `import app.main` completed successfully. |
| Backend health route | Passed | Returned HTTP 200 and `{"status":"ok"}`. |
| Backend automated tests | Passed | `pytest -q` runs 7 isolated SQLite tests covering authentication, JWT rejection, CRUD, cross-user isolation, and atomic planner persistence. |
| PostgreSQL planner persistence | Passed | A deterministic authenticated API call created one `trip` and one `itinerary_day`, then its temporary verification user and cascade-owned records were removed. |
| Security and reliability tests | Passed | The expanded suite covers weak-secret startup rejection, generation rate limiting, Gemini retry behavior, and sub-agent failure fallback. |
| Automated tests | Not implemented | `pytest -q` found no tests. |
| Google OAuth database migration | Passed | `alembic upgrade head` completed; the database was already at `add_google_oauth (head)` and schema inspection confirmed the expected nullable columns and unique index. |
| Live Gemini / Google OAuth sign-in | Not verified in this review | Each requires a real external provider request and credentials. |

## Directory inventory

| Directory | Current state |
| --- | --- |
| `docs/` | Complete PRD and design documentation. |
| `frontend/` | Implemented React application, public image assets, local environment file, and generated `dist/` build output. |
| `backend/app/` | Active FastAPI application, auth, persistence, Gemini service, migrations, and OAuth work in progress. |
| `backend/agents/`, `backend/food/`, `backend/hotel/`, `backend/route/`, `backend/weather/` | Planner and specialised-agent scaffolding; current behavior is mock/stub based. |
| `backend/api/`, `config/`, `database/`, `integrations/`, `middleware/`, `models/`, `routers/`, `schemas/`, `services/`, `tests/`, `utils/` | Empty legacy/scaffold directories; the active code is under `backend/app/`. |
| `assets/`, `database/`, `deployment/`, `scripts/`, `tests/` | Empty top-level scaffold directories. |
| `.claude/`, `.vscode/` | Local tool/editor settings; untracked and not product implementation. |

## Remaining work

1. Complete an end-to-end Google OAuth sign-in test with configured Google credentials.
2. Add the backend test suite and frontend type check to CI; replace the in-process limiter with a shared Redis-backed limiter before horizontally scaling.
3. Expand the current route, hotel, food, and weather context agents into specialised live-data services for transport, activities, reviews, budget, and constraints.
4. Add multi-turn, persisted chat conversations and connect them to saved trip context.
5. Replace remaining mock discovery, maps, booking, and Lost & Found services with authenticated backend endpoints and then live providers where appropriate.
6. Add real Gemini contract tests, browser flows, transaction rollback tests, and provider-integration tests.
7. Add deployment configuration, production environment handling, monitoring, and production security hardening.

## Current milestone

**Phase 2D/E resilient planning baseline.** The app now has a test-backed, authenticated, rate-limited, atomic trip-generation pathway with bounded Gemini retries and partial-data fallbacks. The next meaningful step is expanding the specialist-agent and live-provider coverage.
