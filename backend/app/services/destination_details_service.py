"""Aggregates real data for the destination-details page: geocoding, weather,
activities, and restaurants. Each section degrades independently — one
provider failing (or being unconfigured) never blocks the others, and every
failure is surfaced with an honest reason rather than fabricated content."""
import asyncio
import logging

from app.schemas.destination import DestinationDetailsSchema, PlaceSchema, WeatherDetailSchema
from app.services.integrations.maps import geocode_destination
from app.services.integrations.places import get_activities, get_restaurants
from app.services.integrations.weather import get_weather_detailed

logger = logging.getLogger(__name__)


async def _safe_weather(destination: str) -> WeatherDetailSchema:
    try:
        data = await get_weather_detailed(destination)
        return WeatherDetailSchema(is_realtime_data=True, **data)
    except Exception as exc:
        logger.warning("Weather lookup failed for %r: %s: %s", destination, type(exc).__name__, exc)
        return WeatherDetailSchema(is_realtime_data=False, unavailable_reason="Weather data unavailable")


async def _safe_places(fetcher, latitude: float | None, longitude: float | None, limit: int = 8) -> tuple[list[PlaceSchema], str | None]:
    if latitude is None or longitude is None:
        return [], "Location could not be determined."
    try:
        items = await fetcher(latitude, longitude, limit)
        if not items:
            return [], "No results found nearby."
        return [PlaceSchema(**item) for item in items], None
    except Exception as exc:
        logger.warning("Places lookup failed via %s: %s: %s", getattr(fetcher, "__name__", fetcher), type(exc).__name__, exc)
        return [], "Data currently unavailable"


async def build_destination_details(destination: str) -> DestinationDetailsSchema:
    try:
        coords = await geocode_destination(destination)
        is_realtime_location = True
        latitude, longitude = coords["latitude"], coords["longitude"]
    except Exception:
        is_realtime_location = False
        latitude = longitude = None

    weather, (activities, activities_reason), (restaurants, restaurants_reason) = await asyncio.gather(
        _safe_weather(destination),
        _safe_places(get_activities, latitude, longitude),
        _safe_places(get_restaurants, latitude, longitude),
    )

    return DestinationDetailsSchema(
        destination=destination,
        is_realtime_location=is_realtime_location,
        latitude=latitude,
        longitude=longitude,
        weather=weather,
        activities=activities,
        activities_unavailable_reason=activities_reason,
        restaurants=restaurants,
        restaurants_unavailable_reason=restaurants_reason,
    )
