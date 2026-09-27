# ATLAS — Copilot Instructions

ATLAS is an AI-powered travel planning platform: React/TypeScript/Vite frontend, FastAPI/Python backend, PostgreSQL database, Groq (open-weight LLM) for AI trip generation, plus OpenWeatherMap/OpenTripMap/Foursquare for real destination data.

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL running locally (or a reachable instance)

## 1. Database

Create the database and user once:

```bash
psql -U postgres -c "CREATE USER atlas_user WITH PASSWORD 'change-this-local-password';"
psql -U postgres -c "CREATE DATABASE atlas OWNER atlas_user;"
```

## 2. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Copy the env template and fill it in:

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

Edit `backend/.env`:

| Variable | Required? | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | **Required** | Must be ≥32 bytes or the app refuses to start. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | **Required** | `postgresql+psycopg://atlas_user:<password>@localhost:5432/atlas` |
| `GROQ_API_KEY` | **Required** | AI trip generation and chat won't work without it. Free key, no card: https://console.groq.com/keys |
| `GROQ_MODEL` | Optional | Defaults to `openai/gpt-oss-120b`. List what your account can use: `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"` |
| `OPENWEATHER_API_KEY` | Optional | Real weather on the destination-details page and in the planner's Weather agent. Free at https://openweathermap.org/api. Without it, weather shows "unavailable" — the app still works. |
| `OPENTRIPMAP_API_KEY` | Optional | Real activities/attractions on the destination-details page. Free, no card, at https://opentripmap.io/product. Without it, activities show "unavailable". |
| _(none)_ | — | Restaurants/food places come from OpenStreetMap via the Overpass API, which needs no key. `FOURSQUARE_API_KEY` is no longer used. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | Optional | "Continue with Google" login. Hidden/disabled if unset. |
| `REDIS_URL` | Optional | Shares rate-limit state across multiple backend workers. Falls back to in-process (fine for local/single-worker) if unset. |

Run migrations, then start the server:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`. API docs at `http://127.0.0.1:8000/docs`.

## 3. Frontend setup

```bash
cd frontend
npm install
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

`frontend/.env` only needs one variable:

```
VITE_API_URL=http://localhost:8000
```

Start the dev server:

```bash
npm run dev
```

Open `http://localhost:5173`.

## 4. Running both together

The backend must be running before the frontend can do anything real (auth, trips, planner, destination details) — without it the UI loads but every API call fails. Run them in two terminals:

```bash
# Terminal 1
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

## 5. Verifying it actually works

```bash
cd backend && pytest -q          # expect all tests passing
cd frontend && npx tsc --noEmit  # expect no output (clean)
cd frontend && npm run build     # expect a successful production build
```

Then in the browser: register a user → generate a trip on `/plan` (this calls real Groq + real weather/routing agents, takes ~5-10s) → click any destination card on `/explore` to see real weather/activities/restaurants.

## Known gotchas

- If `GROQ_MODEL` names a model your account can't use, the provider returns 404 and ATLAS fails fast with a clear "does not recognise model" error — list available models with the curl command above rather than guessing.
- Provider rate limits surface as ATLAS's own structured `429` (with `Retry-After`), distinct from the app's per-user limiter.
- If `alembic upgrade head` fails with a connection error, Postgres isn't running or `DATABASE_URL` is wrong — check both before anything else.
- Hotels and flights intentionally have no live-data integration (no free/no-signup provider exists for real pricing or availability) — they're honestly labeled as estimates/unavailable, not a bug.
