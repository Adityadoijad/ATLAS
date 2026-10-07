import asyncio
import logging
from time import monotonic

import httpx

from app.services.integrations.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

maps_breaker = CircuitBreaker()

# Shared User-Agent string matching what the rest of the integrations use.
_USER_AGENT = "ATLAS-Travel-Planning/1.0 (https://github.com/Adityadoijad/ATLAS; student project)"

# Nominatim's usage policy allows at most one request per second from an
# application. Itinerary routing geocodes every stop, so without this a single
# trip would burst a dozen requests and get ATLAS blocked. The lock serialises
# them; the cache means a repeat stop costs nothing at all.
_NOMINATIM_MIN_INTERVAL_SECONDS = 1.0
_nominatim_lock = asyncio.Lock()
_last_request_at = 0.0

# Place names do not move. A day is conservative next to how often OSM changes
# a coordinate, and it keeps reopening an itinerary free.
_PLACE_CACHE_TTL_SECONDS = 24 * 60 * 60
_place_cache: dict[str, tuple[float, dict[str, object] | None]] = {}


class GeocodingUnavailable(RuntimeError):
    """The geocoder could not be reached, or could not place the query."""


async def _throttle() -> None:
    """Hold the caller until one second has passed since the last request."""
    global _last_request_at
    async with _nominatim_lock:
        wait = _NOMINATIM_MIN_INTERVAL_SECONDS - (monotonic() - _last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at = monotonic()


async def geocode_place(query: str) -> dict[str, object] | None:
    """Resolve one free-text place to coordinates, or None if it has no match.

    None means "the geocoder answered and knows of no such place" — a real
    result the caller can report to the user. A geocoder that could not be
    reached raises GeocodingUnavailable instead, because those two are
    different problems with different fixes.

    Returns the geocoder's own `display_name` alongside the coordinates so the
    UI can show which place was actually matched rather than echoing back what
    the user typed.
    """
    key = query.strip().casefold()
    if not key:
        return None

    entry = _place_cache.get(key)
    if entry and monotonic() - entry[0] < _PLACE_CACHE_TTL_SECONDS:
        return entry[1]

    async def request_place() -> dict[str, object] | None:
        await _throttle()
        async with httpx.AsyncClient(
            timeout=8.0, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
        ) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "jsonv2", "limit": 1, "addressdetails": 1,
                        "accept-language": "en"},
            )
            response.raise_for_status()
            results = response.json()
            if not results:
                return None
            top = results[0]
            return {
                "name": query.strip(),
                "display_name": top.get("display_name") or query.strip(),
                "latitude": float(top["lat"]),
                "longitude": float(top["lon"]),
            }

    try:
        place = await maps_breaker.call(request_place)
    except Exception as exc:
        # Never `str(exc)`: httpx stringifies to the request URL. Nominatim
        # needs no key, but the habit is what keeps one from leaking the day an
        # integration here does.
        logger.warning("Geocoding failed for %r: %s", query, type(exc).__name__)
        raise GeocodingUnavailable("The location service could not be reached.") from None

    # A confirmed "no such place" is cached too — re-asking Nominatim the same
    # unanswerable question on every render helps nobody.
    _place_cache[key] = (monotonic(), place)
    return place


async def search_places(query: str, limit: int = 5) -> list[dict[str, object]]:
    """Several candidate places for a partial name, for an autocomplete field.

    Separate from geocode_place because the shapes differ in kind: geocoding
    answers "where is this", search answers "which of these did you mean".
    Returns an empty list when the geocoder knows of no match; raises
    GeocodingUnavailable when it could not be asked.
    """
    text = query.strip()
    if len(text) < 2:
        return []

    async def request_search() -> list[dict[str, object]]:
        await _throttle()
        async with httpx.AsyncClient(
            timeout=8.0, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
        ) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": text, "format": "jsonv2", "limit": limit, "addressdetails": 1,
                        "accept-language": "en"},
            )
            response.raise_for_status()
            results = response.json()
            if not isinstance(results, list):
                return []
            return [
                {
                    # The first comma-separated part is the place itself; the
                    # rest is the administrative trail, kept in display_name.
                    "name": str(item.get("display_name", text)).split(",")[0].strip() or text,
                    "display_name": str(item.get("display_name") or text),
                    "latitude": float(item["lat"]),
                    "longitude": float(item["lon"]),
                }
                for item in results
                if isinstance(item, dict) and item.get("lat") and item.get("lon")
            ]

    try:
        return await maps_breaker.call(request_search)
    except Exception as exc:
        logger.warning("Place search failed for %r: %s", text, type(exc).__name__)
        raise GeocodingUnavailable("The location service could not be reached.") from None


async def geocode_places(queries: list[str]) -> list[dict[str, object] | None]:
    """Resolve several places, in order, one request per second.

    Sequential by design: Nominatim's policy is a hard limit on concurrency,
    not just on rate. Cached entries return immediately and cost no delay, so
    a reopened itinerary resolves instantly.
    """
    resolved: list[dict[str, object] | None] = []
    for query in queries:
        try:
            resolved.append(await geocode_place(query))
        except GeocodingUnavailable:
            # One unreachable lookup must not abandon the rest of the trip.
            resolved.append(None)
    return resolved


async def geocode_destination(destination: str) -> dict[str, float]:
    async def request_geocode() -> dict[str, float]:
        async with httpx.AsyncClient(timeout=4.0, headers={"User-Agent": _USER_AGENT}) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": destination, "format": "jsonv2", "limit": 1},
            )
            response.raise_for_status()
            results = response.json()
            if not results:
                raise LookupError("Destination was not found")
            return {"latitude": float(results[0]["lat"]), "longitude": float(results[0]["lon"])}

    return await maps_breaker.call(request_geocode)


async def validate_india_destination(
    name: str, state: str
) -> dict[str, object] | None:
    """Validate that a Groq-suggested destination actually exists in India.

    Queries Nominatim with "{name}, {state}, India" and confirms the result's
    country_code is "in".  Returns a dict with validated lat/lon/display_name,
    or None when the place cannot be confirmed (not found, not India, or any
    network/service error).

    Never raises — callers discard None results silently so a single bad
    Groq suggestion cannot abort the whole recommendation batch.
    """
    query = f"{name}, {state}, India"
    try:
        async def _request() -> dict[str, object] | None:
            async with httpx.AsyncClient(
                timeout=6.0, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
            ) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "limit": 3,
                        "countrycodes": "in",  # Pre-filter at the API level
                        "addressdetails": 1,
                    },
                )
                response.raise_for_status()
                results = response.json()
                if not results:
                    return None
                # Take the first result with country_code == "in" as a double-
                # check, since the countrycodes param can still return nearby
                # border results for poorly geocoded names.
                for result in results:
                    if (result.get("address") or {}).get("country_code", "").lower() == "in":
                        return {
                            "latitude": float(result["lat"]),
                            "longitude": float(result["lon"]),
                            "display_name": result.get("display_name", query),
                        }
                return None

        return await maps_breaker.call(_request)
    except Exception as exc:
        logger.warning("India destination validation failed for %r: %s", query, type(exc).__name__)
        return None

