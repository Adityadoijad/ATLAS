import asyncio
from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema
from app.services import planner


async def fake_gemini_plan(_: object) -> GeneratedTripPlanSchema:
    return GeneratedTripPlanSchema(
        title="Fallback-safe Goa trip",
        destination="Goa",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 10),
        total_budget=10000,
        days=[
            DayPlanSchema(
                day_number=1,
                date=date(2026, 12, 10),
                title="Baseline day",
                activities=[
                    ActivitySchema(
                        time="09:00",
                        description="Explore local highlights",
                        location="Goa",
                        estimated_cost=0,
                    )
                ],
            )
        ],
    )


async def slow_agent(_: object) -> dict[str, object]:
    await asyncio.sleep(3)
    return {"is_realtime_data": True}


def test_trip_generation_persists_when_realtime_agents_timeout(
    client: TestClient,
    db_session: Session,
    user_a_token: str,
    monkeypatch,
) -> None:
    monkeypatch.setattr(planner, "generate_gemini_trip_plan", fake_gemini_plan)
    for agent in (planner.RouteAgent, planner.HotelAgent, planner.FoodAgent, planner.WeatherAgent):
        monkeypatch.setattr(agent, "run", slow_agent)

    response = client.post(
        "/api/trips/generate",
        json={
            "destination": "Goa",
            "start_date": "2026-12-10",
            "end_date": "2026-12-10",
            "budget": 10000,
            "travelers": 1,
            "preferences": {},
            "currency": "INR",
        },
        headers={"Authorization": f"Bearer {user_a_token}"},
    )

    # The endpoint's established create contract is 201 Created.
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["data_context"]["is_realtime_data"] is False

    trip_id = UUID(payload["id"])
    trip = db_session.query(Trip).filter(Trip.id == trip_id).one()
    assert trip.user_id is not None
    assert trip.destination == "Goa"
    assert trip.itinerary_days
