from pydantic import BaseModel


class LocationSuggestionSchema(BaseModel):
    """One place the geocoder matched.

    `name` is what the user typed or a short label; `display_name` is the
    geocoder's full label ("Nagpur Junction, Nagpur, Maharashtra, India"),
    which is what distinguishes two places that share a short name.
    """

    name: str
    display_name: str
    latitude: float
    longitude: float


class LocationSuggestionsSchema(BaseModel):
    query: str
    results: list[LocationSuggestionSchema] = []
    # Set only when the geocoder could not be reached. An empty `results` with
    # no reason means the geocoder answered and knows of no such place — a
    # different thing, and the UI says so differently.
    unavailable_reason: str | None = None
