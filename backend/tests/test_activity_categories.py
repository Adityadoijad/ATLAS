"""Contract tests for the activity `category` field that drives the trip
cost breakdown, plus the agent-level realtime metadata the itinerary banner
reports against."""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _activity(**overrides) -> dict:
    base = {
        "time": "09:00",
        "description": "Check in",
        "location": "Panaji",
        "estimated_cost": 1000,
        "category": "activity",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("category", ["accommodation", "travel", "food", "activity"])
def test_valid_categories_accepted(category: str) -> None:
    assert ActivitySchema.model_validate(_activity(category=category)).category == category


@pytest.mark.parametrize("category", ["hotel", "meal", "sightseeing", "transport", "misc", "ACTIVITY", "", None])
def test_invalid_categories_rejected(category) -> None:
    """Near-miss values must fail validation so they route through the
    existing retry/fallback path instead of being silently mis-bucketed."""
    with pytest.raises(ValidationError):
        ActivitySchema.model_validate(_activity(category=category))


def test_category_is_required() -> None:
    payload = _activity()
    del payload["category"]
    with pytest.raises(ValidationError):
        ActivitySchema.model_validate(payload)


def test_fallback_plan_still_carries_a_valid_category() -> None:
    """The placeholder plan must satisfy the same schema as a real one."""
    from app.schemas.planner import PlannerRequest
    from app.services.planner_service import _default_plan

    request = PlannerRequest(
        destination="Goa", start_date=date(2026, 12, 10), end_date=date(2026, 12, 10), budget=1000,
    )
    plan = _default_plan(request, fallback_reason="test")
    assert plan.is_realtime_data is False
    assert plan.days[0].activities[0].category == "activity"


def _four_category_plan() -> GeneratedTripPlanSchema:
    return GeneratedTripPlanSchema(
        title="Mixed costs", destination="Goa",
        start_date=date(2026, 12, 10), end_date=date(2026, 12, 10), total_budget=20000,
        days=[DayPlanSchema(day_number=1, date=date(2026, 12, 10), title="Day", activities=[
            ActivitySchema(**_activity(category="accommodation", estimated_cost=5000)),
            ActivitySchema(**_activity(category="travel", estimated_cost=2000)),
            ActivitySchema(**_activity(category="food", estimated_cost=1500)),
            ActivitySchema(**_activity(category="activity", estimated_cost=3000)),
        ])],
    )


def test_persisted_description_round_trips_category(client: TestClient, user_a_token: str, monkeypatch) -> None:
    """The stored itinerary line must carry the category so the frontend can
    build the breakdown without guessing from keywords."""
    from app.services.planner import PlannerResult

    async def fake_plan(_request):
        return PlannerResult(plan=_four_category_plan(), data_context={"is_realtime_data": False})

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_plan)

    response = client.post(
        "/api/trips/generate",
        json={"destination": "Goa", "start_date": "2026-12-10", "end_date": "2026-12-10", "budget": 20000},
        headers=auth(user_a_token),
    )
    assert response.status_code == 201, response.text

    lines = response.json()["itinerary_days"][0]["description"].split("\n")
    assert len(lines) == 4
    categories = [line.split(" | ")[4] for line in lines]
    assert categories == ["accommodation", "travel", "food", "activity"]

    # Costs must survive intact and not be double counted.
    costs = [float(line.split(" | ")[3]) for line in lines]
    assert costs == [5000.0, 2000.0, 1500.0, 3000.0]
    assert sum(costs) == response.json()["itinerary_days"][0]["estimated_cost"] == 11500.0


def test_planner_realtime_status_is_independent_of_agent_fallbacks(monkeypatch) -> None:
    """An agent that can only estimate must not make the planner itself look
    degraded, and every agent's own metadata must survive into data_context.

    Hotel is the remaining estimate-only agent. Food is pinned to its fallback
    here so the test stays deterministic and offline — Food's live path is
    covered in test_food_overpass.py.
    """
    import asyncio

    from app.schemas.planner import PlannerRequest
    from app.services import planner

    async def fake_ai_plan(_request):
        return _four_category_plan()  # is_realtime_data defaults True

    async def realtime_agent(*_args):
        return {"is_realtime_data": True}

    async def estimating_food_agent(*_args):
        return {
            "is_realtime_data": False,
            "cost_is_estimated": True,
            "recommendation": "Reserve roughly 16% of the budget for meals.",
            "fallback_reason": "OpenStreetMap Overpass could not be reached, so meal guidance is estimated.",
        }

    monkeypatch.setattr(planner, "generate_ai_trip_plan", fake_ai_plan)
    monkeypatch.setattr(planner.RouteAgent, "run", realtime_agent)
    monkeypatch.setattr(planner.WeatherAgent, "run", realtime_agent)
    monkeypatch.setattr(planner.FoodAgent, "run", estimating_food_agent)

    request = PlannerRequest(
        destination="Goa", start_date=date(2026, 12, 10), end_date=date(2026, 12, 10), budget=20000,
    )
    result = asyncio.run(planner.generate_trip_plan(request))
    ctx = result.data_context

    # Planner succeeded on its own terms...
    assert ctx["planner"]["is_realtime_data"] is True
    # ...while the aggregate is false purely because other agents estimated.
    assert ctx["is_realtime_data"] is False

    # Per-agent metadata preserved so the UI can name what is actually estimated.
    assert ctx["route"]["is_realtime_data"] is True
    assert ctx["weather"]["is_realtime_data"] is True
    assert ctx["hotel"]["is_realtime_data"] is False
    assert ctx["hotel"]["fallback_reason"]
    assert ctx["food"]["is_realtime_data"] is False
    assert ctx["food"]["fallback_reason"]
