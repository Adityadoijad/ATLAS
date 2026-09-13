from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.destination import DestinationDetailsSchema
from app.services.destination_details_service import build_destination_details

router = APIRouter(prefix="/destinations", tags=["destinations"])


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
