"""Itinerary duration: start and end dates are INCLUSIVE.

Oct 1 -> Oct 8 is eight itinerary days, not seven and certainly not four.

The reported bug: a trip requested for 2026-10-01 to 2026-10-08 generated four
days and was persisted without complaint. Nothing in the pipeline ever counted
the days — the prompt only asked the model to "keep dates within the trip
range", which four days inside the range satisfies, and the schema accepted any
list of at least one day.

These tests pin the count at every layer it passes through: the day-count
helper, the prompt, the schema, the API response and the database rows.
"""
from datetime import date, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.models.itinerary import ItineraryDay
from app.schemas.planner import GeneratedTripPlanSchema, PlannerRequest
from app.services.planner import PlannerResult
from app.services.planner_service import _build_prompt, _default_plan, itinerary_day_count


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _days(start: date, count: int, *, dates: list[date] | None = None, numbers: list[int] | None = None):
    """A well-formed day list, or a deliberately malformed one for the failure cases."""
    dates = dates if dates is not None else [start + timedelta(days=offset) for offset in range(count)]
    numbers = numbers if numbers is not None else list(range(1, len(dates) + 1))
    return [
        {
            "day_number": number,
            "date": day,
            "title": f"Day {number}",
            "activities": [{
                "time": "09:00",
                "description": "Explore",
                "location": "Udaipur",
                "estimated_cost": 500,
                "category": "activity",
            }],
        }
        for number, day in zip(numbers, dates)
    ]


def _plan(start: date, end: date, days) -> GeneratedTripPlanSchema:
    return GeneratedTripPlanSchema(
        title="Trip", destination="Udaipur",
        start_date=start, end_date=end, total_budget=40000, days=days,
    )


# --------------------------------------------------------------------------
# The inclusive count itself
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2026, 10, 1), date(2026, 10, 1), 1),    # single day
        (date(2026, 10, 1), date(2026, 10, 2), 2),
        (date(2026, 10, 1), date(2026, 10, 8), 8),    # the reported case
        (date(2026, 9, 29), date(2026, 10, 2), 4),    # crosses a month
        (date(2026, 12, 30), date(2027, 1, 2), 4),    # crosses a year
        (date(2028, 2, 27), date(2028, 3, 1), 4),     # crosses a leap day
    ],
)
def test_day_count_is_inclusive(start: date, end: date, expected: int) -> None:
    assert itinerary_day_count(start, end) == expected


def test_the_count_is_not_the_elapsed_timedelta() -> None:
    """The distinction the bug turned on: nights vs days."""
    start, end = date(2026, 10, 1), date(2026, 10, 8)
    assert (end - start).days == 7, "seven nights"
    assert itinerary_day_count(start, end) == 8, "eight itinerary days"


# --------------------------------------------------------------------------
# Schema: a short plan is refused
# --------------------------------------------------------------------------

def test_the_reported_case_is_rejected() -> None:
    """Four days for Oct 1-8 used to be accepted and saved."""
    start, end = date(2026, 10, 1), date(2026, 10, 8)
    with pytest.raises(ValidationError) as raised:
        _plan(start, end, _days(start, 4))
    assert "must contain 8 days" in str(raised.value)


def test_the_reported_case_passes_with_eight_days() -> None:
    start, end = date(2026, 10, 1), date(2026, 10, 8)
    plan = _plan(start, end, _days(start, 8))

    assert len(plan.days) == 8
    assert [day.day_number for day in plan.days] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert [day.date.isoformat() for day in plan.days] == [
        "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
        "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
    ]
    assert plan.days[0].date == start
    assert plan.days[-1].date == end


@pytest.mark.parametrize(
    ("start", "end", "count"),
    [
        (date(2026, 10, 1), date(2026, 10, 1), 1),
        (date(2026, 10, 1), date(2026, 10, 2), 2),
        (date(2026, 9, 29), date(2026, 10, 2), 4),
        (date(2026, 12, 30), date(2027, 1, 2), 4),
    ],
)
def test_ranges_of_every_shape_validate_at_their_inclusive_length(
    start: date, end: date, count: int
) -> None:
    plan = _plan(start, end, _days(start, count))
    assert len(plan.days) == count
    assert plan.days[-1].date == end


def test_too_many_days_is_also_rejected() -> None:
    """Padding the itinerary out is no better than truncating it."""
    start, end = date(2026, 10, 1), date(2026, 10, 3)
    with pytest.raises(ValidationError):
        _plan(start, end, _days(start, 5))


def test_a_duplicate_date_is_rejected() -> None:
    start, end = date(2026, 10, 1), date(2026, 10, 3)
    repeated = [date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 3)]
    with pytest.raises(ValidationError) as raised:
        _plan(start, end, _days(start, 3, dates=repeated))
    assert "must be dated" in str(raised.value)


def test_a_missing_calendar_date_is_rejected() -> None:
    """Right count, wrong dates — Oct 2 skipped."""
    start, end = date(2026, 10, 1), date(2026, 10, 3)
    gappy = [date(2026, 10, 1), date(2026, 10, 3), date(2026, 10, 3)]
    with pytest.raises(ValidationError):
        _plan(start, end, _days(start, 3, dates=gappy))


def test_a_date_outside_the_range_is_rejected() -> None:
    start, end = date(2026, 10, 1), date(2026, 10, 3)
    outside = [date(2026, 10, 1), date(2026, 10, 2), date(2026, 11, 9)]
    with pytest.raises(ValidationError):
        _plan(start, end, _days(start, 3, dates=outside))


def test_out_of_order_day_numbers_are_rejected() -> None:
    start, end = date(2026, 10, 1), date(2026, 10, 3)
    with pytest.raises(ValidationError) as raised:
        _plan(start, end, _days(start, 3, numbers=[1, 3, 2]))
    assert "day numbers must run" in str(raised.value)


def test_duplicate_day_numbers_are_rejected() -> None:
    start, end = date(2026, 10, 1), date(2026, 10, 3)
    with pytest.raises(ValidationError):
        _plan(start, end, _days(start, 3, numbers=[1, 1, 2]))


def test_day_numbers_must_start_at_one() -> None:
    start, end = date(2026, 10, 1), date(2026, 10, 3)
    with pytest.raises(ValidationError):
        _plan(start, end, _days(start, 3, numbers=[2, 3, 4]))


def test_an_inverted_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _plan(date(2026, 10, 8), date(2026, 10, 1), _days(date(2026, 10, 8), 1))


# --------------------------------------------------------------------------
# The prompt tells the model the count
# --------------------------------------------------------------------------

def _request(start: date, end: date) -> PlannerRequest:
    return PlannerRequest(destination="Udaipur", start_date=start, end_date=end, budget=40000)


def test_the_prompt_states_the_exact_day_count() -> None:
    """The model used to be told only "keep dates within the trip range",
    which four days inside an eight-day range satisfies."""
    prompt = _build_prompt(_request(date(2026, 10, 1), date(2026, 10, 8)))

    assert "exactly 8 calendar days" in prompt
    assert "2026-10-01 through 2026-10-08 inclusive" in prompt
    assert "exactly 8 entries" in prompt


def test_the_prompt_lists_every_required_date() -> None:
    prompt = _build_prompt(_request(date(2026, 10, 1), date(2026, 10, 8)))
    for offset in range(8):
        assert (date(2026, 10, 1) + timedelta(days=offset)).isoformat() in prompt


def test_the_prompt_handles_a_single_day_trip() -> None:
    prompt = _build_prompt(_request(date(2026, 10, 1), date(2026, 10, 1)))
    assert "exactly 1 calendar days" in prompt or "exactly 1 calendar day" in prompt


# --------------------------------------------------------------------------
# The labelled fallback spans the range too
# --------------------------------------------------------------------------

def test_the_fallback_plan_covers_the_whole_range() -> None:
    """It emitted a single day regardless of the range, which would now fail
    the schema's own coverage rule."""
    plan = _default_plan(_request(date(2026, 10, 1), date(2026, 10, 8)), fallback_reason="test")

    assert len(plan.days) == 8
    assert plan.days[0].date == date(2026, 10, 1)
    assert plan.days[-1].date == date(2026, 10, 8)
    # And it is still honestly marked as not a real AI itinerary.
    assert plan.is_realtime_data is False
    assert plan.fallback_reason == "test"


# --------------------------------------------------------------------------
# Persistence and the API response
# --------------------------------------------------------------------------

def test_every_generated_day_is_persisted_and_returned(
    client: TestClient, db_session, user_a_token: str, monkeypatch
) -> None:
    """End to end for the reported case: 8 days requested, 8 rows written,
    8 days in the response."""
    start, end = date(2026, 10, 1), date(2026, 10, 8)

    async def fake_generate(request):
        return PlannerResult(
            plan=_plan(start, end, _days(start, 8)),
            data_context={"is_realtime_data": False},
        )

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate)

    response = client.post(
        "/api/trips/generate",
        json={
            "destination": "Udaipur",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "budget": 40000,
            "boarding_location": {"name": "Nagpur Railway Station"},
        },
        headers=auth(user_a_token),
    )

    assert response.status_code == 201, response.text
    body = response.json()

    assert len(body["itinerary_days"]) == 8
    assert [day["day_number"] for day in body["itinerary_days"]] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert [day["date"] for day in body["itinerary_days"]] == [
        "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
        "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
    ]

    # The same number of rows actually reached the database.
    rows = db_session.query(ItineraryDay).filter(ItineraryDay.trip_id == UUID(body["id"])).all()
    assert len(rows) == 8


def test_a_reloaded_trip_still_carries_every_day(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    start, end = date(2026, 10, 1), date(2026, 10, 8)

    async def fake_generate(request):
        return PlannerResult(plan=_plan(start, end, _days(start, 8)), data_context={})

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate)

    created = client.post(
        "/api/trips/generate",
        json={
            "destination": "Udaipur",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "budget": 40000,
            "boarding_location": {"name": "Nagpur Railway Station"},
        },
        headers=auth(user_a_token),
    ).json()

    reloaded = client.get(f"/api/trips/{created['id']}", headers=auth(user_a_token)).json()
    assert len(reloaded["itinerary_days"]) == 8
    assert reloaded["itinerary_days"][-1]["date"] == "2026-10-08"


def test_a_long_trip_is_not_capped(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    """No hidden ceiling between the planner and the database."""
    start, end = date(2026, 10, 1), date(2026, 10, 14)

    async def fake_generate(request):
        return PlannerResult(plan=_plan(start, end, _days(start, 14)), data_context={})

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate)

    body = client.post(
        "/api/trips/generate",
        json={
            "destination": "Udaipur",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "budget": 40000,
            "boarding_location": {"name": "Nagpur Railway Station"},
        },
        headers=auth(user_a_token),
    ).json()

    assert len(body["itinerary_days"]) == 14


# --------------------------------------------------------------------------
# The retry tells the model what was wrong
# --------------------------------------------------------------------------

def test_the_first_attempt_carries_no_repair_note() -> None:
    from app.services.planner_service import _repair_note

    assert _repair_note(None, _request(date(2026, 10, 1), date(2026, 10, 8))) == ""


def test_a_retry_names_the_defect_and_the_required_count() -> None:
    """The retry used to re-send a byte-identical prompt.

    On the trip that surfaced this bug the model returned two days for an
    eight-day range, twice — asking again in exactly the same words is a poor
    way to get a different answer.
    """
    from app.services.planner_service import _repair_note

    note = _repair_note(
        ValueError("itinerary must contain 8 days for 2026-10-01 to 2026-10-08 inclusive, but 2 were generated"),
        _request(date(2026, 10, 1), date(2026, 10, 8)),
    )

    assert "PREVIOUS REPLY WAS REJECTED" in note
    assert "but 2 were generated" in note
    assert "exactly 8 day objects" in note


def test_the_retry_reuses_the_failure_from_the_previous_attempt(monkeypatch) -> None:
    """The note must describe the last rejection, not be a fixed string."""
    import asyncio

    from app.services import planner_service

    prompts: list[str] = []
    start, end = date(2026, 10, 1), date(2026, 10, 8)

    async def fake_generate(prompt, system_instruction=None, json_mode=False):
        prompts.append(prompt)
        # Two days for an eight-day range: rejected, then rejected again.
        import json as _json
        return _json.dumps({
            "title": "T", "destination": "Udaipur",
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "total_budget": 40000,
            "days": [
                {"day_number": n, "date": (start + timedelta(days=n - 1)).isoformat(),
                 "title": f"Day {n}",
                 "activities": [{"time": "09:00", "description": "x", "location": "Udaipur",
                                 "estimated_cost": 100, "category": "activity"}]}
                for n in (1, 2)
            ],
        })

    monkeypatch.setattr(planner_service, "generate", fake_generate)

    plan = asyncio.run(planner_service.generate_trip_plan(_request(start, end)))

    assert len(prompts) == 2, "one initial attempt and one repair retry"
    assert "PREVIOUS REPLY WAS REJECTED" not in prompts[0]
    assert "PREVIOUS REPLY WAS REJECTED" in prompts[1]
    assert "but 2 were generated" in prompts[1]

    # And when the model still will not comply, the fallback spans the range
    # and says plainly that it is not a real AI itinerary.
    assert len(plan.days) == 8
    assert plan.is_realtime_data is False
    assert plan.fallback_reason


def test_a_short_plan_is_never_persisted_even_after_retries(monkeypatch) -> None:
    """The guarantee: never fewer days than requested, silently."""
    import asyncio
    import json as _json

    from app.services import planner_service

    start, end = date(2026, 10, 1), date(2026, 10, 8)

    async def always_short(prompt, system_instruction=None, json_mode=False):
        return _json.dumps({
            "title": "T", "destination": "Udaipur",
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "total_budget": 40000,
            "days": [{"day_number": 1, "date": start.isoformat(), "title": "Day 1",
                      "activities": [{"time": "09:00", "description": "x", "location": "Udaipur",
                                      "estimated_cost": 100, "category": "activity"}]}],
        })

    monkeypatch.setattr(planner_service, "generate", always_short)

    plan = asyncio.run(planner_service.generate_trip_plan(_request(start, end)))

    assert len(plan.days) == 8, "the one-day reply never reaches the database"
    assert plan.is_realtime_data is False
