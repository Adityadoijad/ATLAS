"""Application settings loaded from environment variables."""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
    MIN_JWT_SECRET_BYTES = 32
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
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
