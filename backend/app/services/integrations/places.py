"""Real places data for activities/attractions (OpenTripMap) and restaurants
(Foursquare). Both raise when unconfigured or on failure — callers must
surface "unavailable" rather than inventing venues."""
from math import asin, cos, radians, sin, sqrt

import httpx

from app.core.config import settings
from app.services.integrations.circuit_breaker import CircuitBreaker

activities_breaker = CircuitBreaker()
restaurants_breaker = CircuitBreaker()

_EARTH_RADIUS_KM = 6371


def _within_radius(lat1: float, lon1: float, lat2: float | None, lon2: float | None, radius_km: float) -> bool:
    """Foursquare occasionally returns a venue whose own coordinates don't
    match the requested search circle (a real provider data-quality issue,
    e.g. a same-named place indexed on the wrong continent) — don't trust an
    external API's radius filter blindly; verify the distance ourselves."""
    if lat2 is None or lon2 is None:
        return False
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, (lat1, lon1, lat2, lon2))
    d_lat, d_lon = lat2_r - lat1_r, lon2_r - lon1_r
    a = sin(d_lat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(d_lon / 2) ** 2
    distance_km = 2 * _EARTH_RADIUS_KM * asin(sqrt(a))
    return distance_km <= radius_km


async def get_activities(latitude: float, longitude: float, limit: int = 8) -> list[dict[str, object]]:
    if not settings.OPENTRIPMAP_API_KEY:
        raise RuntimeError("OpenTripMap is not configured")

    async def request() -> list[dict[str, object]]:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(
                "https://api.opentripmap.com/0.1/en/places/radius",
                params={
                    "radius": 10000,
                    "lon": longitude,
                    "lat": latitude,
                    "limit": limit * 2,  # over-fetch: unnamed/low-quality entries get filtered below
                    "rate": 1,  # rate=2+ is too sparse outside major landmarks; 1 still excludes junk POIs
                    "format": "json",
                    "apikey": settings.OPENTRIPMAP_API_KEY,
                },
            )
            response.raise_for_status()
            items = response.json()
            results: list[dict[str, object]] = []
            for item in items:
                name = (item.get("name") or "").strip()
                if not name:
                    continue
                point = item.get("point") or {}
                item_lat, item_lon = point.get("lat"), point.get("lon")
                if not _within_radius(latitude, longitude, item_lat, item_lon, radius_km=15):
                    continue
                kinds = (item.get("kinds") or "").split(",")
                results.append({
                    "name": name,
                    "category": kinds[0].replace("_", " ").title() if kinds and kinds[0] else None,
                    "rating": item.get("rate"),
                    "address": None,
                    "latitude": item_lat,
                    "longitude": item_lon,
                    "source": "OpenTripMap",
                })
                if len(results) >= limit:
                    break
            return results

    return await activities_breaker.call(request)


_FOURSQUARE_FOOD_CATEGORY = "4d4b7105d754a06374d81259"  # top-level "Food" category


async def get_restaurants(latitude: float, longitude: float, limit: int = 8) -> list[dict[str, object]]:
    if not settings.FOURSQUARE_API_KEY:
        raise RuntimeError("Foursquare is not configured")

    async def request() -> list[dict[str, object]]:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(
                "https://places-api.foursquare.com/places/search",
                params={
                    "ll": f"{latitude},{longitude}",
                    "radius": 10000,
                    "fsq_category_ids": _FOURSQUARE_FOOD_CATEGORY,
                    "limit": limit,
                },
                headers={
                    "Authorization": f"Bearer {settings.FOURSQUARE_API_KEY}",
                    "Accept": "application/json",
                    # Foursquare's Places API is date-versioned; pin a known-good version.
                    "X-Places-Api-Version": "2025-06-17",
                },
            )
            response.raise_for_status()
            payload = response.json()
            results: list[dict[str, object]] = []
            for item in payload.get("results", []):
                name = (item.get("name") or "").strip()
                if not name:
                    continue
                item_lat, item_lon = item.get("latitude"), item.get("longitude")
                if not _within_radius(latitude, longitude, item_lat, item_lon, radius_km=15):
                    continue
                location = item.get("location") or {}
                categories = item.get("categories") or []
                results.append({
                    "name": name,
                    "category": categories[0].get("name") if categories else None,
                    # The free tier doesn't include ratings (a premium field) —
                    # leave it unset rather than fabricate one.
                    "rating": None,
                    "address": location.get("formatted_address"),
                    "latitude": item_lat,
                    "longitude": item_lon,
                    "source": "Foursquare",
                })
            return results

    return await restaurants_breaker.call(request)
