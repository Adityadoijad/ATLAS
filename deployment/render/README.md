# Deploying ATLAS on Render

The root `render.yaml` Blueprint defines three services:

| Service | Render type | Build/start configuration |
|---|---|---|
| `atlas-api` | Python web service | From `backend/`: `pip install -r requirements.txt`; migrations run with `alembic upgrade head`; starts with `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `atlas-frontend` | Static site | From `frontend/`: `npm ci && npm run build`; publishes `dist/` and rewrites client-side routes to `index.html` |
| `atlas-db` | PostgreSQL | Managed database connected to the API through its internal connection string |

## Setup

1. Push the repository to GitHub and create a Render Blueprint from the branch
   containing `render.yaml`.
2. Set `GROQ_API_KEY` when Render prompts for the unsynced secret. Render
   generates `JWT_SECRET_KEY`; do not replace it with a committed value.
3. Keep the API, database, and persistent disk in the same Render region.
   The API disk is mounted at `/var/data/atlas-uploads` so Lost & Found photos
   survive service deploys and restarts. Persistent disks require a paid web
   service and keep the API to one instance; do not scale that service
   horizontally while uploads are stored locally.
4. The frontend build receives `VITE_API_URL` from the Blueprint. The API's
   `FRONTEND_URL` and `ALLOWED_ORIGINS` must match the deployed frontend origin.
   If you rename either service or attach a custom domain, update those values
   and `VITE_API_URL` to match.
5. To enable Google sign-in, configure `GOOGLE_CLIENT_ID` and
   `GOOGLE_CLIENT_SECRET` on the API, and add
   `https://atlas-api.onrender.com/api/auth/google/callback` (or the matching
   custom-domain URL) to the OAuth client's authorized redirect URIs.
6. Add `OPENWEATHER_API_KEY` and `OPENTRIPMAP_API_KEY` to enable those optional
   live-data integrations. Configure `REDIS_URL` only when shared rate-limit
   state is needed across instances. SMTP settings are optional and enable
   booking confirmation emails.

The Blueprint uses a paid PostgreSQL plan and a paid API instance because the
application needs durable relational data and persistent image storage. The
frontend is a static site. Review Render's current pricing and backup options
before deploying production data. The API adapts Render's `postgres://` /
`postgresql://` database URL to the installed `psycopg` driver.

The frontend's local `.env` is not used by Render; `VITE_API_URL` is injected
at build time. For local setup, continue using the root and service-specific
`.env.example` files.
