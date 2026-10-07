"""Real travel distance and time along a trip's route.

Separate from the trip payload because it is slow and optional: geocoding runs
at one request per second and the itinerary should render immediately without
waiting for it. The frontend loads the itinerary, then fills in travel
metadata as this answers.

Like the weather endpoint, a provider failure is a 200 carrying
`routing_available: false` and a reason. "We could not work out the distance"
is something the itinerary needs to display, not an error that should blank
the page — and it is emphatically not zero kilometres.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.trip import Trip
from app.models.user import User
from app.schemas.routing import TripRouteSchema
from app.services.route_sequence import resolve_sequence

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trips", tags=["routing"])


@router.get("/{trip_id}/route", response_model=TripRouteSchema)
async def get_trip_route(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripRouteSchema:
    """The trip's canonical ordered stops, with a real leg between each pair.

    Both the itinerary timeline and the map route render from this one
    sequence, so they cannot disagree about where the trip starts.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    try:
        stops, legs, unavailable_reason = await resolve_sequence(trip)
    except Exception:
        logger.exception("Unexpected failure building the route for trip %s.", trip_id)
        return TripRouteSchema(
            trip_id=trip_id,
            stops=[],
            legs=[],
            unavailable_reason="Travel times are temporarily unavailable.",
        )

    return TripRouteSchema(
        trip_id=trip_id,
        stops=[stop.as_dict() for stop in stops],  # type: ignore[arg-type]
        legs=[leg.as_dict() for leg in legs],  # type: ignore[arg-type]
        unavailable_reason=unavailable_reason,
    )
