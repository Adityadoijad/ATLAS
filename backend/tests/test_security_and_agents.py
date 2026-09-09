import asyncio
import os
import subprocess
import sys
from datetime import date

from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema, PlannerRequest
from app.services import planner
from app.services import planner_service


def test_startup_rejects_short_jwt_secret() -> None:
    environment = os.environ.copy()
    environment["JWT_SECRET_KEY"] = "too-short"
    result = subprocess.run(
        [sys.executable, "-c", "import app.core.config"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "at least 32 bytes" in result.stderr


def test_sub_agent_failure_returns_fallback_context(monkeypatch) -> None:
    request = PlannerRequest(
        destination="Goa", start_date=date(2026, 12, 10), end_date=date(2026, 12, 10), budget=1000,
    )
    plan = GeneratedTripPlanSchema(
        title="Goa", destination="Goa", start_date=request.start_date, end_date=request.end_date, total_budget=1000,
        days=[DayPlanSchema(day_number=1, date=request.start_date, title="Arrival", activities=[ActivitySchema(time="10:00", description="Check in", location="Panaji", estimated_cost=1000)])],
    )

    async def successful_agent(*_: object) -> dict[str, object]:
        return {"is_realtime_data": True}

    async def failed_agent(*_: object) -> dict[str, object]:
        raise TimeoutError("simulated provider timeout")

    async def fake_gemini(_: PlannerRequest) -> GeneratedTripPlanSchema:
        return plan

    monkeypatch.setattr(planner, "generate_gemini_trip_plan", fake_gemini)
    monkeypatch.setattr(planner.RouteAgent, "run", successful_agent)
    monkeypatch.setattr(planner.HotelAgent, "run", successful_agent)
    monkeypatch.setattr(planner.FoodAgent, "run", successful_agent)
    monkeypatch.setattr(planner.WeatherAgent, "run", failed_agent)

    result = asyncio.run(planner.generate_trip_plan(request))
    assert result.plan == plan
    assert result.data_context["weather"]["is_realtime_data"] is False
    assert "TimeoutError" in result.data_context["weather"]["fallback_reason"]


def test_gemini_generation_retries_transient_failures(monkeypatch) -> None:
    request = PlannerRequest(
        destination="Goa", start_date=date(2026, 12, 10), end_date=date(2026, 12, 10), budget=1000,
    )
    plan = GeneratedTripPlanSchema(
        title="Goa", destination="Goa", start_date=request.start_date, end_date=request.end_date, total_budget=1000,
        days=[DayPlanSchema(day_number=1, date=request.start_date, title="Arrival", activities=[ActivitySchema(time="10:00", description="Check in", location="Panaji", estimated_cost=1000)])],
    )
    attempts = 0

    def flaky_generation(_: PlannerRequest) -> GeneratedTripPlanSchema:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("simulated Gemini rate limit")
        return plan

    async def immediate_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(planner_service, "_generate_plan_sync", flaky_generation)
    monkeypatch.setattr(planner_service.asyncio, "sleep", immediate_sleep)
    assert asyncio.run(planner_service.generate_trip_plan(request)) == plan
    assert attempts == 3
