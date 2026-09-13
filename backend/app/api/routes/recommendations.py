from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.rate_limit import ai_rate_limiter
from app.models.user import User
from app.schemas.recommendations import DiscoveredDestinationSchema, RecommendationSchema
from app.services.discover_service import (
    DiscoveryConfigurationError,
    DiscoveryGenerationError,
    generate_discoveries,
)
from app.services.recommendations import build_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationSchema])
def get_recommendations(current_user: User = Depends(get_current_user)) -> list[RecommendationSchema]:
    """Personalized destination recommendations derived from the user's own
    trip preferences and saved places. Returns a popularity-ranked fallback
    with an honest reason when the user has no history yet."""
    return build_recommendations(current_user)


@router.post("/discover", response_model=list[DiscoveredDestinationSchema])
async def discover_recommendations(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> list[DiscoveredDestinationSchema]:
    """On-demand AI-generated destination suggestions, distinct from the fast
    catalog-based /recommendations above. Real Gemini call — slower, and rate
    limited like the trip planner. Never silently falls back to fake content:
    a genuine AI failure surfaces as an error to the caller."""
    await ai_rate_limiter.enforce(
        request, scope="discover", subject=str(current_user.id), limit=5, window_seconds=60
    )
    try:
        return await generate_discoveries(current_user)
    except DiscoveryConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except DiscoveryGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
