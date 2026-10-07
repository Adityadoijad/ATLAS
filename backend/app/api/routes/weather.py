"""Weather for the frontend.

This endpoint exists so the browser never needs an OpenWeatherMap key: the
key stays in backend configuration, the browser asks ATLAS, and ATLAS asks the
provider. Authenticated, so an unconfigured deployment's quota cannot be
drained by anonymous traffic.

It never returns 5xx for a provider problem. A failed lookup is a successful
200 carrying `is_realtime_data: false` and a reason, because "weather is
unavailable" is information the dashboard needs to render, not an error that
should break the page.
"""
import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.weather import DestinationForecastSchema
from app.services.integrations.weather import WeatherUnavailable, get_destination_forecast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/forecast", response_model=DestinationForecastSchema)
async def get_forecast(
    destination: str = Query(min_length=1, max_length=200),
    current_user: User = Depends(get_current_user),
) -> DestinationForecastSchema:
    """Day-by-day outlook for a destination name."""
    try:
        data = await get_destination_forecast(destination)
    except WeatherUnavailable as exc:
        # The message is written by our own integration, never by the provider,
        # so it cannot contain the request URL or the API key.
        return DestinationForecastSchema(
            destination=destination,
            is_realtime_data=False,
            unavailable_reason=str(exc),
        )
    except Exception:
        logger.exception("Unexpected failure building the forecast for %r.", destination)
        return DestinationForecastSchema(
            destination=destination,
            is_realtime_data=False,
            unavailable_reason="Live weather is temporarily unavailable.",
        )

    return DestinationForecastSchema(
        destination=destination,
        is_realtime_data=True,
        resolved_destination=str(data["resolved_destination"]),
        located_by=str(data["located_by"]),
        latitude=data["latitude"],  # type: ignore[arg-type]
        longitude=data["longitude"],  # type: ignore[arg-type]
        local_date=str(data["local_date"]),
        forecast_through=str(data["forecast_through"]),
        days=data["days"],  # type: ignore[arg-type]
    )
