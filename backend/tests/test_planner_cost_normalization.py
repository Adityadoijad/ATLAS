from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.planner import ActivitySchema, GeneratedTripPlanSchema


def _activity(estimated_cost: object) -> dict:
    return {
        "time": "09:00",
        "description": "Check in",
        "location": "Panaji",
        "estimated_cost": estimated_cost,
    }


@pytest.mark.parametrize(
    "raw, expected",
    [
        (3500, 3500.0),
        (3500.0, 3500.0),
        ("3500", 3500.0),
        ("3500.0", 3500.0),
        ("₹3,500", 3500.0),
        ("3500 INR", 3500.0),
        ("₹3500", 3500.0),
        ("  3500  ", 3500.0),
    ],
)
def test_estimated_cost_normalizes_currency_formatted_values(raw: object, expected: float) -> None:
    activity = ActivitySchema.model_validate(_activity(raw))
    assert activity.estimated_cost == expected


@pytest.mark.parametrize("raw", ["around ₹3,500", "three thousand", "cheap", "unknown", "3500 rupees please"])
def test_estimated_cost_rejects_non_numeric_text(raw: str) -> None:
    with pytest.raises(ValidationError):
        ActivitySchema.model_validate(_activity(raw))


def _plan_payload(total_budget: object) -> dict:
    return {
        "title": "Goa trip",
        "destination": "Goa",
        "start_date": date(2026, 12, 10),
        "end_date": date(2026, 12, 10),
        "total_budget": total_budget,
        "days": [
            {
                "day_number": 1,
                "date": date(2026, 12, 10),
                "title": "Arrival",
                "activities": [_activity(1000)],
            }
        ],
    }


@pytest.mark.parametrize(
    "raw, expected",
    [
        (12000, 12000.0),
        ("12000", 12000.0),
        ("12000.0", 12000.0),
        ("₹12,000", 12000.0),
        ("12000 INR", 12000.0),
    ],
)
def test_total_budget_normalizes_currency_formatted_values(raw: object, expected: float) -> None:
    plan = GeneratedTripPlanSchema.model_validate(_plan_payload(raw))
    assert plan.total_budget == expected


@pytest.mark.parametrize("raw", ["around ₹12,000", "twelve thousand", "unknown"])
def test_total_budget_rejects_non_numeric_text(raw: str) -> None:
    with pytest.raises(ValidationError):
        GeneratedTripPlanSchema.model_validate(_plan_payload(raw))
