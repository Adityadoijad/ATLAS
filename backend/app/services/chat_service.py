"""ATLAS travel-assistant chat.

Thin feature layer over the centralized AI provider in ai_service.py — this
module owns the assistant's behaviour (system instruction), not the provider.

Besides the prose reply, this extracts the structured plan summary the
assistant appends when (and only when) it has produced a complete day-by-day
itinerary. That summary is what lets the UI offer "Proceed to Booking" after a
real plan and stay quiet after an ordinary question, instead of the frontend
guessing from the wording of the reply.
"""
import json
import logging
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.prompts import ATLAS_SYSTEM_INSTRUCTION
from app.schemas.chat import ChatPlanSchema
from app.services.ai_service import generate

logger = logging.getLogger(__name__)

# The trailer the assistant appends after a complete plan (see the system
# instruction). Matched at the very end of the reply and stripped before the
# prose is shown, so the machine-readable block never reaches the chat bubble.
_PLAN_BLOCK_RE = re.compile(r"```atlas-plan\s*(\{.*?\})\s*```\s*\Z", re.DOTALL)
# Any occurrence, wherever it landed. The block is machine-only, so it is
# always removed from the prose even when it is misplaced and therefore not
# honoured as a completed plan.
_ANY_PLAN_BLOCK_RE = re.compile(r"```atlas-plan\s*.*?```", re.DOTALL)


@dataclass
class ChatResult:
    reply: str
    plan: ChatPlanSchema | None = None


def _extract_plan(raw: str) -> ChatResult:
    """Split the assistant's reply into prose and an optional plan summary.

    The trailer is honoured only at the very end of the reply — a block quoted
    mid-conversation is not the assistant completing a plan. It is stripped
    from the prose either way, so the user never sees the machine-readable
    JSON regardless of where the model put it.

    No trailer, a malformed one, or one that fails validation all resolve the
    same way: prose with no plan. That is the safe default — a missing booking
    CTA is a minor loss, whereas offering one after a clarifying question
    would be wrong.
    """
    prose = _ANY_PLAN_BLOCK_RE.sub("", raw).strip()

    # Never hand back an empty bubble. A reply that was only a trailer means
    # something went wrong upstream, so the plan is not trustworthy either.
    if not prose:
        if raw.strip():
            logger.warning("Assistant returned a plan trailer with no prose; returning raw reply.")
        return ChatResult(reply=raw.strip())

    match = _PLAN_BLOCK_RE.search(raw)
    if not match:
        return ChatResult(reply=prose)

    try:
        plan = ChatPlanSchema.model_validate(json.loads(match.group(1)))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        logger.warning("Assistant plan trailer was unusable (%s); returning prose only.", type(exc).__name__)
        return ChatResult(reply=prose)

    if plan.end_date < plan.start_date:
        logger.warning("Assistant plan trailer had end_date before start_date; returning prose only.")
        return ChatResult(reply=prose)

    return ChatResult(reply=prose, plan=plan)


async def chat(user_message: str) -> ChatResult:
    """Send a user message to the configured AI provider and return the reply.

    Raises the provider-neutral errors from ai_service (configuration, quota,
    generation) for the route layer to map onto HTTP responses.
    """
    raw = await generate(user_message, system_instruction=ATLAS_SYSTEM_INSTRUCTION)
    return _extract_plan(raw)
