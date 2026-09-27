"""Application settings loaded from environment variables."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Anchored to this file rather than the process working directory: uvicorn is
# started from several places (repo root, backend/, an IDE, a service manager)
# and a bare load_dotenv() silently finds nothing when the cwd is not backend/.
# The symptom was every AI call failing as "not configured" while .env was
# perfectly fine.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings:
    MIN_JWT_SECRET_BYTES = 32
    # AI provider (Groq). Model is configurable so it is never hardcoded at
    # call sites — see app/services/ai_service.py.
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    OPENTRIPMAP_API_KEY: str = os.getenv("OPENTRIPMAP_API_KEY", "")
    # Outbound email (booking confirmations). Optional: with no SMTP_HOST the
    # app runs exactly as before and the UI hides the email action rather than
    # offering one that always fails.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "ATLAS Travel")
    # STARTTLS on 587 is the common case; SSL-on-connect is port 465.
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in ("1", "true", "yes")
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").strip().lower() in ("1", "true", "yes")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
    _DEFAULT_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5177",
    ]
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    APP_TITLE: str = "ATLAS API"
    APP_VERSION: str = "0.1.0"

    def __init__(self) -> None:
        configured_origins = os.getenv("ALLOWED_ORIGINS", "")
        self.ALLOWED_ORIGINS = [
            origin.strip().rstrip("/")
            for origin in (
                configured_origins.split(",")
                if configured_origins
                else [*self._DEFAULT_ALLOWED_ORIGINS, self.FRONTEND_URL]
            )
            if origin.strip()
        ]
        secret_length = len(self.JWT_SECRET_KEY.encode("utf-8"))
        if secret_length < self.MIN_JWT_SECRET_BYTES:
            raise RuntimeError(
                "JWT_SECRET_KEY must be at least 32 bytes. Generate a cryptographically random secret before starting ATLAS."
            )


settings = Settings()
