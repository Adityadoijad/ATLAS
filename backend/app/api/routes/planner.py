from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import ai_rate_limiter
from app.models.itinerary import ItineraryDay
from app.models.trip import Trip
from app.models.user import User
from app.schemas.planner import BoardingLocation, PlannerRequest
from app.schemas.trip import TripResponse
from app.services.integrations.maps import GeocodingUnavailable, geocode_place
from app.services.place_resolver import verify_plan_locations
from app.services.planner import PlannerResult, generate_trip_plan
from app.services.planner_service import (
    PlannerConfigurationError,
    PlannerGenerationError,
    PlannerQuotaExceededError,
    PlannerValidationError,
)

router = APIRouter(prefix="/trips", tags=["planner"])


async def _resolve_boarding_location(boarding: BoardingLocation | None) -> BoardingLocation:
    """Turn the typed starting point into coordinates, or refuse the trip.

    Three outcomes, deliberately distinct:
      * not supplied      -> 422, because the first route leg has no origin
                             and the alternatives (destination centre, first
                             hotel, browser location) would all be guesses
                             presented as the user's own choice;
      * geocoder says no  -> 422 naming what was typed, so it can be corrected;
      * geocoder is down  -> 503, a temporary condition worth retrying, never
                             a silent substitution.
    """
    if boarding is None or not boarding.name.strip():
        raise HTTPException(
            status_code=422,
            detail="A boarding location is required so the itinerary can start where your journey does.",
        )

    try:
        resolved = await geocode_place(boarding.name)
    except GeocodingUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="The location service is unavailable right now, so your starting point could not be confirmed. Please try again shortly.",
        ) from exc

    if resolved is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"We could not find a place called {boarding.name.strip()!r}. "
                "Try a more specific starting point, such as a station, airport or full address."
            ),
        )

    return BoardingLocation(
        name=boarding.name.strip(),
        display_name=str(resolved["display_name"]),
        latitude=float(resolved["latitude"]),
        longitude=float(resolved["longitude"]),
    )


@router.post("/generate", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def generate_and_save_trip(
    request: PlannerRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Trip:
    await ai_rate_limiter.enforce(
        http_request,
        scope="trip-generate",
        subject=str(current_user.id),
        limit=3,
        window_seconds=60,
    )
    if request.end_date < request.start_date:
        raise HTTPException(status_code=422, detail="end_date must not be before start_date")

    boarding = await _resolve_boarding_location(request.boarding_location)
    # The planner sees the resolved location, so the prompt and the route agree
    # on which place the trip starts from.
    request = request.model_copy(update={"boarding_location": boarding})

    try:
        generated: PlannerResult = await generate_trip_plan(request)
    except PlannerQuotaExceededError as exc:
        # The AI provider's own quota, not ATLAS's rate limiter — a distinct
        # 429 so the client can tell "you're going too fast" apart from
        # "the AI provider's daily/per-minute quota is exhausted."
        raise HTTPException(
            status_code=429,
            detail="The AI provider's free-tier quota is exhausted right now. Please try again shortly.",
            headers={"Retry-After": "60"},
        ) from exc
    except PlannerConfigurationError as exc:
        raise HTTPException(status_code=503, detail="AI planner is not configured.") from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PlannerGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    plan = generated.plan

    # Check the planner actually named real places, and repair the ones a safe
    # deterministic edit can rescue. This mutates `plan` before it is written,
    # so the traveller sees names ATLAS can find — and it warms the geocoder
    # cache, so the route endpoint answers immediately afterwards. An
    # unresolvable name is left exactly as written: its travel time reports as
    # unavailable rather than being filled in with a guess.
    resolution = await verify_plan_locations(plan, request.destination, boarding.name)
    data_context = {**generated.data_context, "places": resolution.as_dict()}

    if plan.start_date != request.start_date or plan.end_date != request.end_date:
        raise HTTPException(status_code=502, detail="The AI planner returned dates outside the requested trip.")

    user_id = current_user.id
    # Authentication queries start a transaction. End it before opening the single
    # write transaction that guarantees the trip and every itinerary day persist together.
    db.rollback()
    with db.begin():
        trip = Trip(
            user_id=user_id,
            title=plan.title,
            destination=plan.destination,
            start_date=plan.start_date,
            end_date=plan.end_date,
            travelers=request.travelers,
            budget=plan.total_budget,
            preferences=request.preferences,
            currency=request.currency.upper(),
            status="upcoming",
            # Recorded now so a later e-ticket can state honestly which parts
            # were live data and which were AI estimates.
            data_context=data_context,
            boarding_location=boarding.model_dump(),
        )
        db.add(trip)
        db.flush()
        for day in plan.days:
            db.add(ItineraryDay(
                trip_id=trip.id,
                day_number=day.day_number,
                date=day.date,
                title=day.title,
                # Pipe-delimited so the frontend can reconstruct each activity.
                # Category is last so older rows (4 fields) still parse, just
                # without a category.
                description="\n".join(
                    f"{activity.time} | {activity.description} | {activity.location} | {activity.estimated_cost} | {activity.category}"
                    for activity in day.activities
                ),
                estimated_cost=sum(activity.estimated_cost for activity in day.activities),
            ))

    db.refresh(trip)
    trip.data_context = data_context
    return trip
