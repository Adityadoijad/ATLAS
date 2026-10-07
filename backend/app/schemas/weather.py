from pydantic import BaseModel


class ForecastDaySchema(BaseModel):
    """One day of provider forecast, on the destination's local calendar."""

    date: str
    weekday: str
    temperature_c: float
    temperature_min_c: float
    temperature_max_c: float
    condition: str | None = None
    icon: str | None = None
    step_count: int
    local_time_of_summary: str


class DestinationForecastSchema(BaseModel):
    """The weather the frontend is allowed to render.

    `is_realtime_data` is the whole contract: when it is false there are no
    days, only a reason. The frontend has nothing to fall back on and must say
    weather is unavailable, because there is no honest alternative to show.
    """

    destination: str
    is_realtime_data: bool
    # What OpenWeatherMap says it geocoded the requested name to. Null when the
    # lookup failed, so the UI never labels numbers with a place it guessed at.
    resolved_destination: str | None = None
    # "geocoder" or "provider_name_match". OpenWeatherMap's own name matching
    # is ambiguous (its "Manali" is in Chennai), so a name-matched result is
    # flagged rather than presented as equally trustworthy.
    located_by: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    # The destination's current date, not the server's. A user in IST looking at
    # a trip to Lisbon should see Lisbon's days.
    local_date: str | None = None
    forecast_through: str | None = None
    days: list[ForecastDaySchema] = []
    unavailable_reason: str | None = None
