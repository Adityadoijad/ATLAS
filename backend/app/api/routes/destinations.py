import logging

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.destination import DestinationDetailsSchema
from app.schemas.recommendations import DiscoverIndiaDestinationSchema
from app.services.destination_details_service import build_destination_details
from app.services.discover_india_service import get_india_recommendations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.get("/recommendations", response_model=list[DiscoverIndiaDestinationSchema])
async def get_india_destination_recommendations(
    request: Request,
) -> list[DiscoverIndiaDestinationSchema]:
    """AI-curated India destination recommendations for the home page.

    Public endpoint — no authentication required so first-time visitors see
    the Discover India section immediately. Results are cached for 6-10 hours
    so Groq is not called on every page load.

    On Groq failure: returns the controlled fallback dataset (clearly not AI).
    On complete failure: returns an empty list (frontend shows graceful state).
    Never returns 500 for a working frontend.
    """
    return await get_india_recommendations()


@router.get("/{destination}/details", response_model=DestinationDetailsSchema)
async def get_destination_details(
    destination: str,
    current_user: User = Depends(get_current_user),
) -> DestinationDetailsSchema:
    """Real weather, activities, and restaurants for a destination name (works
    for both the catalog's fixed destinations and freeform/AI-discovered
    names). Each section is independently marked unavailable on failure
    rather than showing fabricated data."""
    return await build_destination_details(destination)

