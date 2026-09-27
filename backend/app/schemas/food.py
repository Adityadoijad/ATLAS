from typing import Literal

from pydantic import BaseModel

# OSM amenity values ATLAS treats as food places. Kept open as a plain string
# in the schema (below) because OSM tagging evolves, but this tuple is what the
# Overpass query actually asks for.
FoodCategory = Literal["restaurant", "cafe", "fast_food", "food_court", "bakery", "ice_cream", "pub", "bar"]


class FoodPlaceSchema(BaseModel):
    """One eating place as OpenStreetMap knows it.

    Every field except name/coordinates/source is optional because OSM
    coverage is uneven — a village bakery may have nothing but a name. An
    absent tag is None; it is never filled in with a plausible guess.

    Note there is deliberately no price field: OSM carries no reliable menu
    pricing, so meal costs remain an explicit AI estimate elsewhere rather
    than being passed off as live data.
    """

    name: str
    category: str | None = None
    cuisine: str | None = None
    latitude: float
    longitude: float
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    opening_hours: str | None = None
    source: str = "openstreetmap"
    is_realtime_data: bool = True
