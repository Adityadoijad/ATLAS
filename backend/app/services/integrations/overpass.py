"""Live food-place data from OpenStreetMap via the Overpass API.

Free and keyless, which is why it replaces the paid-tier places providers for
food. Overpass runs on donated public infrastructure, so this module is
deliberately conservative: one short-timeout request per destination, results
cached for 20 minutes, concurrent callers for the same area share a single
in-flight request, and a rate-limit response is never retried.

What this gives us is *place* information (name, cuisine, contact, opening
hours) that is current in OSM. It is NOT table availability and NOT menu
pricing — OSM has no reliable price data, so meal costs stay an explicit
estimate elsewhere. Missing tags stay None; nothing here is invented.

Data © OpenStreetMap contributors, ODbL.
"""
import asyncio
import logging
from time import time

import httpx

from app.services.integrations.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

food_breaker = CircuitBreaker()

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"

# The main front door load-balances across instances and periodically returns
# 504 while an instance behind it is unhealthy, even when our rate-limit slots
# are free. One failover to a named public instance covers that without
# hammering anything: each endpoint is tried at most once per lookup, and a
# genuine rate-limit response (429) stops the whole thing immediately.
_ENDPOINTS = (OVERPASS_ENDPOINT, "https://z.overpass-api.de/api/interpreter")

# Identify the project, per the Overpass usage policy.
_USER_AGENT = "ATLAS-Travel-Planner/1.0 (https://github.com/Adityadoijad/ATLAS; student project)"

# Everywhere someone eats. Alcohol-led venues are opt-in (see include_bars)
# rather than mixed into a family trip's default recommendations.
_FOOD_AMENITIES = ("restaurant", "cafe", "fast_food", "food_court", "bakery", "ice_cream")
_BAR_AMENITIES = ("pub", "bar")

DEFAULT_RADIUS_M = 5000

# Overpass is shared infrastructure and restaurants do not change minute to
# minute, so repeat planning for the same city is served from memory.
_CACHE_TTL_SECONDS = 20 * 60
_cache: dict[tuple, tuple[float, list[dict[str, object]]]] = {}
# One shared task per cache key: two users planning the same destination at
# the same moment must not become two Overpass requests.
_inflight: dict[tuple, asyncio.Task] = {}

# Overpass's own query timeout, and our HTTP ceiling on top of it. Kept short
# so a slow public server degrades to the estimate path instead of holding up
# the planner.
_QUERY_TIMEOUT_SECONDS = 12
_HTTP_TIMEOUT_SECONDS = 15.0


class OverpassRateLimited(RuntimeError):
    """Overpass rate limited us (HTTP 429). Never retried, never failed over."""


class OverpassUnavailable(RuntimeError):
    """Overpass failed or returned something unusable."""


def _cache_key(latitude: float, longitude: float, radius_m: int, amenities: tuple[str, ...]) -> tuple:
    # Coordinates are rounded to ~100 m so tiny geocoder jitter for the same
    # city still hits the same cache entry.
    return (round(latitude, 3), round(longitude, 3), radius_m, amenities)


def build_query(latitude: float, longitude: float, radius_m: int, amenities: tuple[str, ...]) -> str:
    """Overpass QL for every food amenity within the radius.

    `nwr` covers nodes, ways and relations (a mall food court is often a way),
    and `out center tags` gives one representative coordinate per element
    regardless of which of those it is.
    """
    clauses = "\n  ".join(
        f'nwr["amenity"="{amenity}"](around:{radius_m},{latitude},{longitude});'
        for amenity in amenities
    )
    return f"[out:json][timeout:{_QUERY_TIMEOUT_SECONDS}];\n(\n  {clauses}\n);\nout center tags;"


def _coordinates(element: dict) -> tuple[float | None, float | None]:
    """Nodes carry lat/lon directly; ways and relations carry a `center`."""
    if element.get("lat") is not None and element.get("lon") is not None:
        return element["lat"], element["lon"]
    center = element.get("center") or {}
    return center.get("lat"), center.get("lon")


def _address(tags: dict[str, str]) -> str | None:
    """Assemble a street address from OSM's addr:* tags.

    Returns None rather than a partial fragment when the tags are too sparse
    to be useful — a bare house number helps nobody.
    """
    street = tags.get("addr:street")
    if not street:
        return None
    parts = [tags.get("addr:housenumber"), street]
    line = " ".join(part for part in parts if part)
    for extra in ("addr:suburb", "addr:city", "addr:postcode"):
        if tags.get(extra):
            line = f"{line}, {tags[extra]}"
    return line or None


def _cuisine(tags: dict[str, str]) -> str | None:
    """OSM packs multiple cuisines into one semicolon-separated tag."""
    raw = tags.get("cuisine")
    if not raw:
        return None
    cuisines = [part.strip().replace("_", " ") for part in raw.split(";") if part.strip()]
    return ", ".join(cuisines) or None


def normalize_element(element: dict) -> dict[str, object] | None:
    """Turn one Overpass element into a FoodPlace dict.

    Returns None for anything unusable — an unnamed amenity or one with no
    coordinates cannot be recommended to a traveller. Every optional tag that
    is absent stays None; no value is ever guessed.
    """
    tags = element.get("tags") or {}
    name = (tags.get("name") or "").strip()
    if not name:
        return None

    latitude, longitude = _coordinates(element)
    if latitude is None or longitude is None:
        return None

    return {
        "name": name,
        "category": tags.get("amenity"),
        "cuisine": _cuisine(tags),
        "latitude": latitude,
        "longitude": longitude,
        "address": _address(tags),
        "phone": tags.get("phone") or tags.get("contact:phone") or None,
        "website": tags.get("website") or tags.get("contact:website") or None,
        "opening_hours": tags.get("opening_hours") or None,
        "source": "openstreetmap",
        "is_realtime_data": True,
    }


def _deduplicate(places: list[dict[str, object]]) -> list[dict[str, object]]:
    """Drop repeats of the same venue.

    OSM frequently holds both a node and an enclosing building way for one
    restaurant, and chains repeat a name across a city. Keyed on name plus
    coordinates rounded to ~100 m so the duplicate pair collapses while two
    genuine branches a few streets apart both survive. Richer records win, so
    deduplication never costs us a phone number or opening hours.
    """
    best: dict[tuple, dict[str, object]] = {}
    for place in places:
        key = (
            str(place["name"]).casefold(),
            round(float(place["latitude"]), 3),
            round(float(place["longitude"]), 3),
        )
        filled = sum(1 for field in ("cuisine", "address", "phone", "website", "opening_hours") if place.get(field))
        existing = best.get(key)
        if existing is None or filled > existing[0]:
            best[key] = (filled, place)
    return [place for _, place in best.values()]


async def _post(client: httpx.AsyncClient, endpoint: str, query: str) -> list[dict[str, object]]:
    response = await client.post(endpoint, data={"data": query})

    # 429 means we personally are over the limit. Retrying anywhere is exactly
    # what the usage policy forbids, so this aborts the lookup outright.
    if response.status_code == 429:
        logger.warning("Overpass rate limited ATLAS (HTTP 429); using the estimate path.")
        raise OverpassRateLimited("Overpass returned HTTP 429.")
    if response.status_code >= 400:
        raise OverpassUnavailable(f"Overpass returned HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError as exc:
        # Overpass reports query errors as an HTML page with a 200 status.
        raise OverpassUnavailable("Overpass returned a response that was not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise OverpassUnavailable("Overpass returned an unexpected payload shape.")

    return [
        normalized_place
        for element in payload.get("elements", [])
        if isinstance(element, dict) and (normalized_place := normalize_element(element)) is not None
    ]


async def _request(latitude: float, longitude: float, radius_m: int, amenities: tuple[str, ...]) -> list[dict[str, object]]:
    query = build_query(latitude, longitude, radius_m, amenities)
    last_error: Exception | None = None

    async with httpx.AsyncClient(
        timeout=_HTTP_TIMEOUT_SECONDS, headers={"User-Agent": _USER_AGENT}
    ) as client:
        for endpoint in _ENDPOINTS:
            try:
                return _deduplicate(await _post(client, endpoint, query))
            except OverpassRateLimited:
                raise
            except (OverpassUnavailable, httpx.HTTPError) as exc:
                logger.warning(
                    "Overpass endpoint %s unavailable (%s); %s.",
                    endpoint, type(exc).__name__,
                    "trying the next instance" if endpoint != _ENDPOINTS[-1] else "falling back to estimates",
                )
                last_error = exc

    raise OverpassUnavailable(str(last_error) if last_error else "Overpass is unavailable.")


async def get_food_places(
    latitude: float,
    longitude: float,
    *,
    radius_m: int = DEFAULT_RADIUS_M,
    include_bars: bool = False,
) -> list[dict[str, object]]:
    """Food places near a point, from OpenStreetMap.

    Raises OverpassRateLimited or OverpassUnavailable on failure; callers must
    fall back rather than present estimates as live data. An empty list means
    Overpass answered but knows of no food places there.
    """
    amenities = _FOOD_AMENITIES + _BAR_AMENITIES if include_bars else _FOOD_AMENITIES
    key = _cache_key(latitude, longitude, radius_m, amenities)

    entry = _cache.get(key)
    if entry and time() - entry[0] < _CACHE_TTL_SECONDS:
        return entry[1]

    existing = _inflight.get(key)
    if existing is not None:
        # Someone is already asking Overpass for this exact area — wait on
        # their request instead of issuing a second one. `shield` keeps a
        # cancelled waiter from killing the shared task for everyone else.
        return await asyncio.shield(existing)

    async def run() -> list[dict[str, object]]:
        try:
            places = await food_breaker.call(lambda: _request(latitude, longitude, radius_m, amenities))
            _cache[key] = (time(), places)
            return places
        finally:
            _inflight.pop(key, None)

    task = asyncio.ensure_future(run())
    _inflight[key] = task
    return await asyncio.shield(task)
