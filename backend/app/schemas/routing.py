from uuid import UUID

from pydantic import BaseModel


class RouteStopSchema(BaseModel):
    index: int
    # What the itinerary calls this place.
    label: str
    # What was sent to the geocoder — the label qualified with the destination
    # city, so "Mall Road" does not resolve to a different country.
    query: str
    latitude: float | None = None
    longitude: float | None = None
    is_boarding: bool = False
    resolved: bool = False


class RouteLegSchema(BaseModel):
    """Travel between two consecutive stops.

    `distance_km` and `duration_minutes` are null together, and only when the
    router could not answer. They are never 0 as a stand-in: zero is a real
    answer meaning the two stops are the same place, and using it for "unknown"
    would tell the traveller a journey takes no time at all.
    """

    from_index: int
    to_index: int
    distance_km: float | None = None
    duration_minutes: float | None = None
    routing_available: bool = False


class TripRouteSchema(BaseModel):
    trip_id: UUID
    stops: list[RouteStopSchema] = []
    legs: list[RouteLegSchema] = []
    # Set when the whole route could not be computed. Individual legs can also
    # be unavailable while others succeed, which this does not cover.
    unavailable_reason: str | None = None
