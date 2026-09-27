"""Real places data for activities/attractions (OpenTripMap) and restaurants
(OpenStreetMap via Overpass). Both raise when unconfigured or on failure —
callers must surface "unavailable" rather than inventing venues."""
from math import asin, cos, radians, sin, sqrt

import httpx

from app.core.config import settings
from app.services.integrations.circuit_breaker import CircuitBreaker
from app.services.integrations.overpass import get_food_places

activities_breaker = CircuitBreaker()

_EARTH_RADIUS_KM = 6371


def _within_radius(lat1: float, lon1: float, lat2: float | None, lon2: float | None, radius_km: float) -> bool:
    """A provider occasionally returns a place whose own coordinates don't
    match the requested search circle (a real data-quality issue, e.g. a
    same-named place indexed on the wrong continent) — don't trust an external
    API's radius filter blindly; verify the distance ourselves."""
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


async def get_restaurants(latitude: float, longitude: float, limit: int = 8) -> list[dict[str, object]]:
    """Nearby eating places from OpenStreetMap.

    Replaces the previous Foursquare lookup: Overpass is keyless and free,
    and it carries cuisine, opening hours and contact details that the free
    Foursquare tier withheld. Shares the cache and rate-limit discipline in
    overpass.py, so the details page and the planner's food agent never make
    two separate calls for the same city.
    """
    places = await get_food_places(latitude, longitude)
    return [
        {
            "name": place["name"],
            # OSM amenity values are snake_case ("fast_food"); present them
            # the way the rest of the UI writes categories.
            "category": str(place["category"]).replace("_", " ").title() if place.get("category") else None,
            "cuisine": place.get("cuisine"),
            # OSM has no ratings. None keeps the UI from showing a star it
            # cannot justify, rather than inventing a score.
            "rating": None,
            "address": place.get("address"),
            "phone": place.get("phone"),
            "website": place.get("website"),
            "opening_hours": place.get("opening_hours"),
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "source": "OpenStreetMap",
        }
        for place in places[:limit]
    ]
