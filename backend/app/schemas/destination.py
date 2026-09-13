from pydantic import BaseModel


class ForecastEntrySchema(BaseModel):
    timestamp: str
    temperature_c: float
    condition: str
    icon: str | None = None


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
    rating: float | None = None
    address: str | None = None
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
