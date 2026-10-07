"""OpenWeatherMap access for ATLAS.

Two things in here are load-bearing for honesty:

*Dates.* OpenWeatherMap's free plan serves 3-hourly steps covering five days.
Anything past that is not a forecast we hold, so ATLAS must not present one.
The steps themselves are UTC, while a traveller thinks in the destination's
local calendar — 21:00 UTC is already tomorrow in Manali. Every day bucket
here is therefore built from `dt` shifted by the city's own UTC offset, which
the provider returns alongside the forecast.

*Errors.* `httpx.HTTPStatusError` stringifies to the full request URL, and the
API key travels in that URL as `appid`. So no provider exception is ever
re-raised, logged or returned as-is: failures are converted to
`WeatherUnavailable` with a message this module wrote itself. That is the only
reason the conversion exists, and it is why callers should not reach for
`str(exc)` on anything httpx raised.

Nothing here invents weather. A lookup either returns provider data or raises.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from time import monotonic

import httpx

from app.core.config import settings
from app.services.integrations.circuit_breaker import CircuitBreaker
from app.services.integrations.maps import geocode_destination

logger = logging.getLogger(__name__)

weather_breaker = CircuitBreaker()
forecast_breaker = CircuitBreaker()

_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

# What the free plan actually covers. Used to decide whether a trip's dates
# fall inside a real forecast or only inside wishful thinking.
FORECAST_HORIZON_DAYS = 5

# A day bucket needs this many 3-hourly steps (~9 hours) before its min/max is
# worth printing. The provider's window ends mid-day, so the final bucket is
# usually a stub and is dropped rather than shown as a full day.
_MIN_STEPS_PER_DAY = 3

# OpenWeatherMap's free tier has a hard call-per-day/per-minute ceiling.
# Caching per destination means repeat trip generation and dashboard loads for
# the same city are served from memory instead of re-hitting the API — this is
# the guard against silently blowing through that ceiling.
_CACHE_TTL_SECONDS = 60 * 60
_DEGRADED_CACHE_TTL_SECONDS = 5 * 60
_current_cache: dict[str, tuple[float, dict[str, object]]] = {}
_detailed_cache: dict[str, tuple[float, dict[str, object]]] = {}
_forecast_cache: dict[str, tuple[float, dict[str, object]]] = {}


class WeatherUnavailable(RuntimeError):
    """Weather could not be obtained. Carries no provider text, hence no key."""


def _cache_key(destination: str) -> str:
    """Destination-scoped, so one city's weather can never be served for another.

    Case and surrounding whitespace only; nothing else is folded away, so
    "Manali" and "Manali, Himachal Pradesh" stay separate cache entries because
    they are separate provider queries with separate answers.
    """
    return destination.strip().casefold()


def _cache_get(cache: dict[str, tuple[float, dict[str, object]]], key: str) -> dict[str, object] | None:
    entry = cache.get(key)
    if entry is None:
        return None
    stamp, value = entry
    # A result the geocoder did not place is held only briefly: it may be the
    # wrong city, and an hour is a long time to serve Chennai's weather for a
    # trip to Himachal. It self-corrects as soon as the geocoder recovers.
    ttl = _CACHE_TTL_SECONDS if value.get("located_by") != "provider_name_match" else _DEGRADED_CACHE_TTL_SECONDS
    # monotonic() cannot jump backwards over a clock change, so an entry can
    # never appear fresh for longer than its TTL.
    if monotonic() - stamp < ttl:
        return value
    return None


def _cache_set(cache: dict[str, tuple[float, dict[str, object]]], key: str, value: dict[str, object]) -> None:
    # Only ever called on a successful provider response. A failure is raised,
    # never stored, so a broken lookup cannot be replayed as live data.
    cache[key] = (monotonic(), value)


def _unavailable_reason(status_code: int) -> str:
    """A reason worth showing a user, written here rather than by the provider."""
    if status_code == 401:
        return "The configured OpenWeatherMap API key was rejected."
    if status_code == 404:
        return "OpenWeatherMap does not recognise that destination."
    if status_code == 429:
        return "The OpenWeatherMap request quota is exhausted."
    if status_code >= 500:
        return "OpenWeatherMap is temporarily unavailable."
    return "OpenWeatherMap could not answer the request."


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    destination: str,
    coordinates: tuple[float, float] | None = None,
) -> dict[str, object]:
    """One provider call, with every failure mode sanitised.

    Nothing that escapes this function contains the request URL, so nothing
    downstream can accidentally publish the API key.

    Coordinates are preferred over the name. OpenWeatherMap's `q=` matching is
    ambiguous in a way that fails silently: `q=Manali` resolves to a
    neighbourhood of Chennai, 2,000 km from the Himachal town, and still comes
    back labelled "Manali, IN". Pinning lat/lon removes the ambiguity and keeps
    weather on the same place the route and restaurant agents used.
    """
    location: dict[str, object] = (
        {"lat": coordinates[0], "lon": coordinates[1]} if coordinates else {"q": destination}
    )
    try:
        response = await client.get(
            url, params={**location, "appid": settings.OPENWEATHER_API_KEY, "units": "metric"}
        )
    except httpx.HTTPError as exc:
        # `type(exc).__name__` only: httpx puts the full URL in the message.
        logger.warning(
            "OpenWeatherMap unreachable for %r (%s).", destination, type(exc).__name__
        )
        raise WeatherUnavailable("OpenWeatherMap could not be reached.") from None

    if response.status_code >= 400:
        logger.warning(
            "OpenWeatherMap returned %s for %r — treating as unavailable.",
            response.status_code, destination,
        )
        raise WeatherUnavailable(_unavailable_reason(response.status_code)) from None

    try:
        payload = response.json()
    except ValueError:
        raise WeatherUnavailable("OpenWeatherMap returned an unreadable response.") from None
    if not isinstance(payload, dict):
        raise WeatherUnavailable("OpenWeatherMap returned an unexpected payload.") from None
    return payload


def _require_key() -> None:
    if not settings.OPENWEATHER_API_KEY:
        raise WeatherUnavailable("Live weather is not configured on this server.")


async def _through_breaker(breaker: CircuitBreaker, operation):
    """Run a provider call behind its breaker, keeping one exception type out.

    An open breaker raises a bare RuntimeError. Letting that escape would make
    every caller handle two unrelated failure types for the same user-visible
    outcome, so it is translated here.
    """
    try:
        return await breaker.call(operation)
    except WeatherUnavailable:
        raise
    except RuntimeError as exc:
        if "circuit is open" not in str(exc):
            raise
        raise WeatherUnavailable(
            "Live weather is paused after repeated provider failures."
        ) from None


# --------------------------------------------------------------------------
# Current conditions
# --------------------------------------------------------------------------

async def get_weather(destination: str) -> dict[str, object]:
    """Current conditions. Explicitly *not* a forecast — see get_trip_weather."""
    _require_key()

    key = _cache_key(destination)
    cached = _cache_get(_current_cache, key)
    if cached is not None:
        return cached

    coordinates = await _resolve_coordinates(destination)

    async def request_weather() -> dict[str, object]:
        async with httpx.AsyncClient(timeout=4.0) as client:
            payload = await _get_json(client, _CURRENT_URL, destination, coordinates)
            return {
                "temperature_c": payload["main"]["temp"],
                "condition": payload["weather"][0]["description"],
                # Echoed so a caller can check the provider resolved the name it
                # asked for, instead of assuming it did.
                "resolved_destination": _resolved_name(payload),
            }

    result = await _through_breaker(weather_breaker, request_weather)
    _cache_set(_current_cache, key, result)
    return result


def _resolved_name(payload: dict[str, object]) -> str | None:
    """What the provider says it actually geocoded to."""
    name = payload.get("name")
    country = (payload.get("sys") or {}).get("country") if isinstance(payload.get("sys"), dict) else None
    if not name:
        return None
    return f"{name}, {country}" if country else str(name)


async def get_weather_detailed(destination: str) -> dict[str, object]:
    """Full current conditions + short forecast for the destination-details page.

    Raises WeatherUnavailable on failure — the caller is responsible for
    surfacing "unavailable" rather than fabricating weather.
    """
    _require_key()

    key = _cache_key(destination)
    cached = _cache_get(_detailed_cache, key)
    if cached is not None:
        return cached

    coordinates = await _resolve_coordinates(destination)

    async def request_current() -> dict[str, object]:
        async with httpx.AsyncClient(timeout=4.0) as client:
            return await _get_json(client, _CURRENT_URL, destination, coordinates)

    current = await _through_breaker(weather_breaker, request_current)

    forecast: list[dict[str, object]] = []
    try:
        daily = await get_destination_forecast(destination)
    except WeatherUnavailable:
        # The forecast is a bonus; current conditions alone are still valid.
        daily = None
    if daily is not None:
        for day in daily["days"]:  # type: ignore[index]
            forecast.append({
                "timestamp": day["date"],
                "weekday": day["weekday"],
                "temperature_c": day["temperature_c"],
                "condition": day["condition"],
                "icon": day["icon"],
            })

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


# --------------------------------------------------------------------------
# Daily forecast, bucketed by the destination's own calendar
# --------------------------------------------------------------------------

def _bucket_by_local_day(
    steps: list[dict[str, object]], offset: timedelta
) -> dict[date, list[tuple[datetime, dict[str, object]]]]:
    buckets: dict[date, list[tuple[datetime, dict[str, object]]]] = {}
    for step in steps:
        epoch = step.get("dt")
        if not isinstance(epoch, (int, float)):
            continue
        # `dt` is UTC; the traveller's day is the destination's day.
        local = datetime.fromtimestamp(epoch, tz=timezone.utc) + offset
        buckets.setdefault(local.date(), []).append((local, step))
    return buckets


def _summarize_day(day: date, steps: list[tuple[datetime, dict[str, object]]]) -> dict[str, object] | None:
    temperatures: list[float] = []
    minima: list[float] = []
    maxima: list[float] = []
    for _, step in steps:
        main = step.get("main")
        if not isinstance(main, dict):
            continue
        for source, target in ((("temp",), temperatures), (("temp_min",), minima), (("temp_max",), maxima)):
            value = main.get(source[0])
            if isinstance(value, (int, float)):
                target.append(float(value))
    if not temperatures:
        return None

    # The condition shown for a day is the one nearest local midday — the part
    # of the day a traveller is actually out in, and not an average of
    # descriptions, which would be meaningless.
    midday_local, midday_step = min(steps, key=lambda item: abs(item[0].hour - 12))
    weather = midday_step.get("weather")
    entry = weather[0] if isinstance(weather, list) and weather and isinstance(weather[0], dict) else {}

    return {
        "date": day.isoformat(),
        "weekday": day.strftime("%a"),
        "temperature_c": round(float((midday_step.get("main") or {}).get("temp", temperatures[0])), 1),
        "temperature_min_c": round(min(minima or temperatures), 1),
        "temperature_max_c": round(max(maxima or temperatures), 1),
        "condition": entry.get("description"),
        "icon": entry.get("icon"),
        # How much of the day the provider actually covered, so a caller can
        # tell a full day from the partial one at either end of the window.
        "step_count": len(steps),
        "local_time_of_summary": midday_local.strftime("%H:%M"),
    }


async def _resolve_coordinates(destination: str) -> tuple[float, float] | None:
    """Where the destination actually is, via the geocoder ATLAS uses elsewhere.

    Nominatim ranks by prominence, so "Manali" is the Himachal town. Returning
    None is acceptable: the caller then falls back to the provider's own name
    matching, which is worse but better than no weather.
    """
    try:
        coords = await geocode_destination(destination)
    except Exception as exc:
        logger.info(
            "Could not geocode %r for weather (%s); falling back to provider name matching.",
            destination, type(exc).__name__,
        )
        return None
    return float(coords["latitude"]), float(coords["longitude"])


async def get_destination_forecast(destination: str) -> dict[str, object]:
    """Day-by-day outlook for a destination, on the destination's local calendar.

    Raises WeatherUnavailable on any failure. `days` holds only days the
    provider genuinely covered; it is never padded out to a tidy five.
    """
    _require_key()

    key = _cache_key(destination)
    cached = _cache_get(_forecast_cache, key)
    if cached is not None:
        return cached

    coordinates = await _resolve_coordinates(destination)

    async def request_forecast() -> dict[str, object]:
        async with httpx.AsyncClient(timeout=6.0) as client:
            return await _get_json(client, _FORECAST_URL, destination, coordinates)

    payload = await _through_breaker(forecast_breaker, request_forecast)

    city = payload.get("city") if isinstance(payload.get("city"), dict) else {}
    steps = payload.get("list")
    if not isinstance(steps, list) or not steps:
        raise WeatherUnavailable("OpenWeatherMap returned no forecast for that destination.")

    offset = timedelta(seconds=int(city.get("timezone") or 0))
    local_today = (datetime.now(tz=timezone.utc) + offset).date()

    buckets = _bucket_by_local_day([step for step in steps if isinstance(step, dict)], offset)

    days: list[dict[str, object]] = []
    for day in sorted(buckets):
        # Today is kept even when partial (the morning has simply passed); a
        # partial day at the far end of the window is dropped, because its
        # min/max would be drawn from a couple of night-time readings.
        if len(buckets[day]) < _MIN_STEPS_PER_DAY and day != local_today:
            continue
        summary = _summarize_day(day, buckets[day])
        if summary is not None:
            days.append(summary)

    if not days:
        raise WeatherUnavailable("OpenWeatherMap returned no usable forecast days.")

    coord = city.get("coord") if isinstance(city.get("coord"), dict) else {}
    result: dict[str, object] = {
        # The provider's own idea of what it answered about, so the UI can show
        # which place the numbers describe rather than echoing the user's
        # spelling back at them.
        "resolved_destination": (
            f"{city['name']}, {city['country']}"
            if city.get("name") and city.get("country")
            else city.get("name") or destination
        ),
        # Which lookup produced the location, so a wrong-city result is
        # diagnosable instead of invisible.
        "located_by": "geocoder" if coordinates else "provider_name_match",
        "latitude": coordinates[0] if coordinates else coord.get("lat"),
        "longitude": coordinates[1] if coordinates else coord.get("lon"),
        "timezone_offset_seconds": int(city.get("timezone") or 0),
        "local_date": local_today.isoformat(),
        "forecast_through": days[-1]["date"],
        "days": days,
    }
    _cache_set(_forecast_cache, key, result)
    return result


async def get_trip_weather(
    destination: str, start_date: date, end_date: date
) -> dict[str, object]:
    """Weather for a trip's own dates where the provider reaches them.

    A trip starting inside the five-day window gets a forecast for its actual
    days. A trip further out gets the next few days labelled as a current
    outlook, with `covers_trip_dates` false — because no free provider knows
    what December looks like in September, and pretending otherwise is the
    failure mode this whole module exists to avoid.
    """
    data = await get_destination_forecast(destination)
    all_days: list[dict[str, object]] = list(data["days"])  # type: ignore[arg-type]

    trip_days = [
        day for day in all_days
        if start_date <= date.fromisoformat(str(day["date"])) <= end_date
    ]

    return {
        **data,
        "days": trip_days or all_days,
        "covers_trip_dates": bool(trip_days),
        "scope": "trip_dates" if trip_days else "current_outlook",
        "trip_start_date": start_date.isoformat(),
        "trip_end_date": end_date.isoformat(),
        "note": (
            f"Forecast for your travel dates in {data['resolved_destination']}."
            if trip_days
            else (
                f"Current {len(all_days)}-day outlook for {data['resolved_destination']}. "
                f"A forecast for {start_date.isoformat()} is beyond the "
                f"{FORECAST_HORIZON_DAYS}-day provider window and will appear closer to departure."
            )
        ),
    }
