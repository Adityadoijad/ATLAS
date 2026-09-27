"""Tests for the structured plan summary the assistant attaches to a completed
itinerary, which gates the "Proceed to Booking" CTA in the UI.

The contract: a plan is returned only for a genuinely complete itinerary, the
machine-readable trailer never reaches the user's chat bubble, and anything
doubtful degrades to "no plan" rather than offering booking for a reply that
was only a question.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.services import chat_service

PLAN_JSON = (
    '{"title": "5-Day Goa Beach & Food Trip", "destination": "Goa", '
    '"start_date": "2026-12-10", "end_date": "2026-12-14", "travelers": 2, '
    '"estimated_cost": 28500, "currency": "INR"}'
)


def _reply_with(trailer: str, prose: str = "Here is your plan.\n\n**Day 1** — Arrive in Goa.") -> str:
    return f"{prose}\n\n```atlas-plan\n{trailer}\n```"


def test_complete_plan_is_extracted_and_stripped_from_the_prose() -> None:
    result = chat_service._extract_plan(_reply_with(PLAN_JSON))

    assert result.plan is not None
    assert result.plan.destination == "Goa"
    assert result.plan.travelers == 2
    assert result.plan.estimated_cost == 28500.0
    assert str(result.plan.start_date) == "2026-12-10"
    # The machine-readable block must never reach the chat bubble.
    assert "atlas-plan" not in result.reply
    assert result.reply.endswith("Arrive in Goa.")


def test_ordinary_answer_has_no_plan() -> None:
    """A direct travel question must not offer a booking CTA."""
    result = chat_service._extract_plan(
        "The best time to visit Kerala is between October and March."
    )
    assert result.plan is None
    assert result.reply.startswith("The best time")


def test_clarifying_question_has_no_plan() -> None:
    result = chat_service._extract_plan("Which beach destination did you have in mind, and for how long?")
    assert result.plan is None


@pytest.mark.parametrize(
    "trailer",
    [
        "{not json at all",                                   # malformed JSON
        '{"destination": "Goa"}',                             # missing required fields
        PLAN_JSON.replace('"travelers": 2', '"travelers": 0'),  # invalid traveller count
        PLAN_JSON.replace('"estimated_cost": 28500', '"estimated_cost": "about thirty thousand"'),
        PLAN_JSON.replace('"start_date": "2026-12-10"', '"start_date": "not-a-date"'),
    ],
)
def test_unusable_trailer_degrades_to_prose_only(trailer: str) -> None:
    """A bad trailer must never surface a CTA — and must never crash the chat."""
    result = chat_service._extract_plan(_reply_with(trailer))
    assert result.plan is None
    assert "Day 1" in result.reply


def test_currency_formatted_cost_is_normalized() -> None:
    """Reuses the planner's normalizer, so a model that writes ₹28,500 despite
    the prompt still produces a usable number instead of dropping the CTA."""
    result = chat_service._extract_plan(
        _reply_with(PLAN_JSON.replace('"estimated_cost": 28500', '"estimated_cost": "\\u20b928,500"'))
    )
    assert result.plan is not None
    assert result.plan.estimated_cost == 28500.0


def test_end_date_before_start_date_is_rejected() -> None:
    result = chat_service._extract_plan(
        _reply_with(PLAN_JSON.replace('"end_date": "2026-12-14"', '"end_date": "2026-12-01"'))
    )
    assert result.plan is None


def test_trailer_without_prose_returns_the_raw_reply() -> None:
    """An empty chat bubble would be worse than a stray block, and a reply that
    is only a trailer means something went wrong upstream."""
    result = chat_service._extract_plan(f"```atlas-plan\n{PLAN_JSON}\n```")
    assert result.plan is None
    assert result.reply


def test_trailer_is_only_honoured_at_the_end_of_the_reply() -> None:
    """A block quoted mid-conversation (e.g. the user pasted one) must not be
    mistaken for the assistant completing a plan."""
    result = chat_service._extract_plan(
        f"```atlas-plan\n{PLAN_JSON}\n```\n\nThat block above is just an example of the format."
    )
    assert result.plan is None


def test_chat_endpoint_returns_the_plan(client: TestClient, monkeypatch) -> None:
    async def fake_generate(*_args, **_kwargs):
        return _reply_with(PLAN_JSON)

    monkeypatch.setattr("app.services.chat_service.generate", fake_generate)
    response = client.post("/api/chat", json={"message": "Plan a 5-day Goa trip for 2 under 30000"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert "atlas-plan" not in body["response"]
    assert body["plan"]["destination"] == "Goa"
    assert body["plan"]["travelers"] == 2
    assert body["plan"]["estimated_cost"] == 28500.0


def test_chat_endpoint_omits_plan_for_a_plain_question(client: TestClient, monkeypatch) -> None:
    async def fake_generate(*_args, **_kwargs):
        return "Try Appam with Stew and Karimeen Pollichathu."

    monkeypatch.setattr("app.services.chat_service.generate", fake_generate)
    response = client.post("/api/chat", json={"message": "What food should I try in Kerala?"})

    assert response.status_code == 200, response.text
    assert response.json()["plan"] is None


def test_chat_service_returns_a_result_object(monkeypatch) -> None:
    """The route depends on this shape; keep it from silently reverting to str."""
    async def fake_generate(*_args, **_kwargs):
        return _reply_with(PLAN_JSON)

    monkeypatch.setattr("app.services.chat_service.generate", fake_generate)
    result = asyncio.run(chat_service.chat("Plan a Goa trip"))

    assert isinstance(result, chat_service.ChatResult)
    assert result.plan is not None


def test_system_prompt_documents_the_trailer_contract() -> None:
    """The extractor is useless if the model was never told to emit the block."""
    from app.core.prompts import ATLAS_SYSTEM_INSTRUCTION

    assert "```atlas-plan" in ATLAS_SYSTEM_INSTRUCTION
    assert "ONLY when" in ATLAS_SYSTEM_INSTRUCTION
