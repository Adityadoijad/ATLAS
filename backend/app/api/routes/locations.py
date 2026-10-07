"""Place lookup for the frontend.

Exists so the boarding-location field can offer real suggestions without the
browser talking to Nominatim directly. Going through ATLAS keeps one
User-Agent and one rate limiter in front of the geocoder, which is what its
usage policy asks for — a browser fanning out requests per keystroke from
every user's IP is exactly what gets an application blocked.

Authenticated, for the same reason: an open proxy to a donated geocoding
service is not something to leave lying around.
"""
import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.location import LocationSuggestionSchema, LocationSuggestionsSchema
from app.services.integrations.maps import GeocodingUnavailable, search_places

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/search", response_model=LocationSuggestionsSchema)
async def search_locations(
    q: str = Query(min_length=2, max_length=200),
    current_user: User = Depends(get_current_user),
) -> LocationSuggestionsSchema:
    """Places matching a partial name, for the boarding-location field.

    An empty result and an unavailable geocoder are reported differently: the
    first means "no such place", the second means "ask again shortly", and a
    user who typed a real station name deserves to know which one happened.
    """
    try:
        results = await search_places(q)
    except GeocodingUnavailable as exc:
        return LocationSuggestionsSchema(
            query=q,
            results=[],
            unavailable_reason=str(exc),
        )

    return LocationSuggestionsSchema(
        query=q,
        results=[LocationSuggestionSchema(**item) for item in results],
    )
