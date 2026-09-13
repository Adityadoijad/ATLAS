from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.itinerary import ItineraryDay
from app.models.trip import Trip
from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema
from app.services.planner import PlannerResult


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def fake_generate_trip_plan(_: object) -> PlannerResult:
    return PlannerResult(plan=GeneratedTripPlanSchema(
        title="Structured Goa trip",
        destination="Goa",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 11),
        total_budget=25000,
        days=[
            DayPlanSchema(day_number=1, date=date(2026, 12, 10), title="Arrival", activities=[ActivitySchema(time="10:00", description="Check in", location="Panaji", estimated_cost=2000)]),
            DayPlanSchema(day_number=2, date=date(2026, 12, 11), title="Beach day", activities=[ActivitySchema(time="09:00", description="Visit beach", location="Candolim", estimated_cost=1000)]),
        ],
    ), data_context={"is_realtime_data": False})


def test_generate_trip_persists_trip_and_days_atomically(client: TestClient, db_session: Session, user_a_token: str, monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate_trip_plan)
    response = client.post("/api/trips/generate", json={
        "destination": "Goa",
        "start_date": "2026-12-10",
        "end_date": "2026-12-11",
        "budget": 25000,
        "travelers": 2,
        "preferences": {"interests": ["beaches"]},
        "currency": "INR",
    }, headers=auth(user_a_token))
    assert response.status_code == 201, response.text
    assert response.json()["data_context"]["is_realtime_data"] is False
    trip_id = UUID(response.json()["id"])
    assert db_session.query(Trip).filter(Trip.id == trip_id).count() == 1
    assert db_session.query(ItineraryDay).filter(ItineraryDay.trip_id == trip_id).count() == 2


def test_trip_generation_rate_limit(client: TestClient, user_a_token: str, monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate_trip_plan)
    payload = {
        "destination": "Goa", "start_date": "2026-12-10", "end_date": "2026-12-11",
        "budget": 25000, "travelers": 2, "preferences": {}, "currency": "INR",
    }
    for _ in range(3):
        assert client.post("/api/trips/generate", json=payload, headers=auth(user_a_token)).status_code == 201
    limited = client.post("/api/trips/generate", json=payload, headers=auth(user_a_token))
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
