from pydantic import BaseModel


class ForecastEntrySchema(BaseModel):
    timestamp: str
    temperature_c: float
    condition: str
    icon: str | None = None
    # Computed on the destination's local calendar. The browser must not derive
    # it from `timestamp`: a date-only string parses as UTC midnight, so any
    # viewer west of UTC would be shown the previous weekday.
    weekday: str | None = None


class WeatherDetailSchema(BaseModel):
    is_realtime_data: bool
    temperature_c: float | None = None
    feels_like_c: float | None = None
    humidity_percent: int | None = None
    wind_speed_ms: float | None = None
    condition: str | None = None
    icon: str | None = None
    forecast: list[ForecastEntrySchema] = []
    unavailable_reason: str | None = None


class PlaceSchema(BaseModel):
    name: str
    category: str | None = None
    # OpenStreetMap carries these for food places; OpenTripMap attractions
    # leave them unset. Optional everywhere so a missing tag stays missing
    # instead of being filled in with a plausible-looking value.
    cuisine: str | None = None
    rating: float | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    opening_hours: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source: str


class DestinationDetailsSchema(BaseModel):
    destination: str
    is_realtime_location: bool
    latitude: float | None = None
    longitude: float | None = None
    weather: WeatherDetailSchema
    activities: list[PlaceSchema] = []
    activities_unavailable_reason: str | None = None
    restaurants: list[PlaceSchema] = []
    restaurants_unavailable_reason: str | None = None


class DestinationPhotoSchema(BaseModel):
    """A real photograph of a destination, or an honest absence.

    Every field is nullable together. `url` of None means no genuine photo of
    this place was found — the UI then draws a neutral placeholder rather than
    a picture of somewhere else, which is the bug this endpoint exists to end.
    """

    destination: str
    url: str | None = None
    source: str | None = None
    source_url: str | None = None
    author: str | None = None
    license: str | None = None
