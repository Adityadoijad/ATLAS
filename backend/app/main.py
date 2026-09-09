"""
ATLAS FastAPI application factory.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.api.routes.chat import router as chat_router
from app.api.routes.auth import router as auth_router
from app.api.routes.trips import router as trips_router
from app.api.routes.saved_places import router as saved_places_router
from app.api.routes.planner import router as planner_router

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL or "memory://",
)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        description="ATLAS AI-Powered Travel Planning Backend — Phase 2B",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Session Middleware (Required for OAuth state tracking) ────────────────
    # Cross-site OAuth redirects require a Secure SameSite=None state cookie in
    # production. Starlette exposes these attributes directly; Partitioned is
    # not supported by the installed Starlette release.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.JWT_SECRET_KEY,
        same_site="none" if settings.FRONTEND_URL.startswith("https://") else "lax",
        https_only=settings.FRONTEND_URL.startswith("https://"),
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Only allow the local frontend origins. Extend this list in production
    # once the frontend is deployed.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Health check")
    async def health():
        return {"status": "ok"}

    # ── API routes ────────────────────────────────────────────────────────────
    app.include_router(auth_router, prefix="/api")
    app.include_router(trips_router, prefix="/api")
    app.include_router(planner_router, prefix="/api")
    app.include_router(saved_places_router, prefix="/api")
    app.include_router(chat_router, prefix="/api", tags=["Chat"])

    return app


app = create_app()
