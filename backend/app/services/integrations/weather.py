import logging
from datetime import date, datetime, timedelta

import httpx

from app.core.config import settings
from app.services.integrations.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

weather_breaker = CircuitBreaker()
forecast_breaker = CircuitBreaker()

# OpenWeatherMap's free tier has a hard call-per-day/per-minute ceiling.
# Caching per (destination, day) means repeat trip-generation calls for the
# same city on the same day are served from memory instead of re-hitting the
# API — this is the guard against silently blowing through that ceiling.
_CACHE_TTL = timedelta(hours=1)
_current_cache: dict[tuple[str, str], tuple[datetime, dict[str, object]]] = {}
_detailed_cache: dict[tuple[str, str], tuple[datetime, dict[str, object]]] = {}


def _cache_key(destination: str) -> tuple[str, str]:
    return (destination.strip().lower(), date.today().isoformat())


def _cache_get(cache: dict[tuple[str, str], tuple[datetime, dict[str, object]]], key: tuple[str, str]) -> dict[str, object] | None:
    entry = cache.get(key)
    if entry and datetime.utcnow() - entry[0] < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(cache: dict[tuple[str, str], tuple[datetime, dict[str, object]]], key: tuple[str, str], value: dict[str, object]) -> None:
    cache[key] = (datetime.utcnow(), value)


def _raise_for_status_logged(response: httpx.Response, destination: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 429):
            logger.warning(
                "OpenWeatherMap returned %s for %r — treating as unavailable "
                "(auth/quota issue, not an ATLAS bug).",
                exc.response.status_code, destination,
            )
        raise


async def get_weather(destination: str) -> dict[str, object]:
    """Minimal current-conditions lookup used by the planner's Weather agent."""
    if not settings.OPENWEATHER_API_KEY:
        raise RuntimeError("OpenWeatherMap is not configured")

    key = _cache_key(destination)
    cached = _cache_get(_current_cache, key)
    if cached is not None:
        return cached

    async def request_weather() -> dict[str, object]:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": destination, "appid": settings.OPENWEATHER_API_KEY, "units": "metric"},
            )
            _raise_for_status_logged(response, destination)
            payload = response.json()
            return {
                "temperature_c": payload["main"]["temp"],
                "condition": payload["weather"][0]["description"],
            }

    result = await weather_breaker.call(request_weather)
    _cache_set(_current_cache, key, result)
    return result


async def get_weather_detailed(destination: str) -> dict[str, object]:
    """Full current conditions + short forecast for the destination-details page.
    Raises on failure — the caller is responsible for surfacing "unavailable"
    rather than fabricating weather."""
    if not settings.OPENWEATHER_API_KEY:
        raise RuntimeError("OpenWeatherMap is not configured")

    key = _cache_key(destination)
    cached = _cache_get(_detailed_cache, key)
    if cached is not None:
        return cached

    async def request_current() -> dict[str, object]:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": destination, "appid": settings.OPENWEATHER_API_KEY, "units": "metric"},
            )
            _raise_for_status_logged(response, destination)
            return response.json()

    async def request_forecast() -> dict[str, object]:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={"q": destination, "appid": settings.OPENWEATHER_API_KEY, "units": "metric"},
            )
            _raise_for_status_logged(response, destination)
            return response.json()

    current = await weather_breaker.call(request_current)
    forecast: list[dict[str, object]] = []
    try:
        forecast_payload = await forecast_breaker.call(request_forecast)
        # The forecast API returns 3-hour steps; take one entry per day (every 8th = 24h).
        for entry in forecast_payload.get("list", [])[::8][:5]:
            forecast.append({
                "timestamp": entry["dt_txt"],
                "temperature_c": entry["main"]["temp"],
                "condition": entry["weather"][0]["description"],
                "icon": entry["weather"][0].get("icon"),
            })
    except Exception:
        forecast = []  # Forecast is a bonus — current conditions alone are still valid.

    result = {
        "temperature_c": current["main"]["temp"],
        "feels_like_c": current["main"]["feels_like"],
        "humidity_percent": current["main"]["humidity"],
        "wind_speed_ms": current["wind"]["speed"],
        "condition": current["weather"][0]["description"],
        "icon": current["weather"][0].get("icon"),
        "forecast": forecast,
    }
    _cache_set(_detailed_cache, key, result)
    return result
