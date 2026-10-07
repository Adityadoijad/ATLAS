from app.schemas.planner import PlannerRequest
from app.services.integrations.weather import WeatherUnavailable, get_trip_weather


class WeatherAgent:
    name = "weather"

    # Two sequential round trips, not one: the destination is geocoded first
    # (so weather lands on the same place the route and food agents used), then
    # OpenWeatherMap is queried by coordinate. The planner's 2.5s default was
    # enough for a single call and is not enough for two — a cold lookup timed
    # out and reported "live weather unavailable" for a working provider. Kept
    # under the sum of the two client timeouts (4s + 6s) so a genuinely slow
    # provider still degrades instead of stalling the planner, which runs these
    # agents concurrently with AI generation anyway.
    timeout_seconds = 8.0

    async def run(self, request: PlannerRequest) -> dict[str, object]:
        """Weather for the trip being planned — its destination and its dates.

        `is_realtime_data` is true only when the provider answered. It says
        nothing about whether the days returned are the *trip's* days: a trip
        months out gets a live current outlook with `covers_trip_dates` false,
        which is live data that simply does not reach the travel dates. The
        planner and the UI read both flags.
        """
        try:
            weather = await get_trip_weather(
                request.destination, request.start_date, request.end_date
            )
        except WeatherUnavailable as exc:
            # Our own message, so no provider URL and no API key can reach
            # data_context, the API response or the database.
            return {
                "is_realtime_data": False,
                "forecast": None,
                "fallback_reason": str(exc),
            }
        except Exception as exc:
            return {
                "is_realtime_data": False,
                "forecast": None,
                "fallback_reason": f"Live weather failed unexpectedly ({type(exc).__name__}).",
            }

        return {"is_realtime_data": True, **weather}
