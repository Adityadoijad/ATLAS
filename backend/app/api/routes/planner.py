from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import ai_rate_limiter
from app.models.itinerary import ItineraryDay
from app.models.trip import Trip
from app.models.user import User
from app.schemas.planner import PlannerRequest
from app.schemas.trip import TripResponse
from app.services.planner import PlannerResult, generate_trip_plan
from app.services.planner_service import PlannerConfigurationError, PlannerGenerationError, PlannerValidationError

router = APIRouter(prefix="/trips", tags=["planner"])


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
        limit=5,
        window_seconds=60,
    )
    if request.end_date < request.start_date:
        raise HTTPException(status_code=422, detail="end_date must not be before start_date")

    try:
        generated: PlannerResult = await generate_trip_plan(request)
    except PlannerConfigurationError as exc:
        raise HTTPException(status_code=503, detail="AI planner is not configured.") from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PlannerGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    plan = generated.plan

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
        )
        db.add(trip)
        db.flush()
        for day in plan.days:
            db.add(ItineraryDay(
                trip_id=trip.id,
                day_number=day.day_number,
                date=day.date,
                title=day.title,
                description="\n".join(
                    f"{activity.time} | {activity.description} | {activity.location} | {activity.estimated_cost}"
                    for activity in day.activities
                ),
                estimated_cost=sum(activity.estimated_cost for activity in day.activities),
            ))

    db.refresh(trip)
    trip.data_context = generated.data_context
    return trip
