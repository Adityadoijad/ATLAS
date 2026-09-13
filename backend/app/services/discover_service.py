"""AI-generated ("Discover more") destination suggestions — on-demand, real
Gemini calls, distinct from the fast catalog-based recommendations in
recommendations.py. Slower and quota-bound like the trip planner, so this is
opt-in behind its own endpoint rather than loaded automatically on every page
view.

No silent fallback: if Gemini can't produce valid suggestions, this raises
rather than fabricating fake "AI discoveries" — matching the same honesty
requirement enforced in planner_service.py.
"""
import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.models.user import User
from app.schemas.recommendations import DiscoveredDestinationSchema
from app.services.recommendations import CATALOG, _build_tag_profile

logger = logging.getLogger(__name__)


class DiscoveryConfigurationError(RuntimeError):
    pass


class DiscoveryGenerationError(RuntimeError):
    pass


def _profile_summary(user: User) -> str:
    tag_profile = _build_tag_profile(list(user.trips), list(user.saved_places))
    if not tag_profile:
        return "This traveller has no history yet — suggest broadly appealing destinations for a first trip."
    top_tags = sorted(tag_profile, key=lambda tag: tag_profile[tag], reverse=True)[:5]
    return f"This traveller's interests, most to least frequent: {', '.join(top_tags)}."


def _generate_sync(user: User) -> list[DiscoveredDestinationSchema]:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise DiscoveryConfigurationError("The Gemini SDK is not installed.") from exc
    if not settings.GEMINI_API_KEY:
        raise DiscoveryConfigurationError("GEMINI_API_KEY is not set.")

    exclude_names = ", ".join(str(item["name"]) for item in CATALOG)
    prompt = f"""Suggest exactly 3 real, existing travel destinations for a traveller
booking from India, as a JSON array (JSON array only, no surrounding object).

{_profile_summary(user)}

Do NOT suggest any of these destinations (already shown elsewhere in the app):
{exclude_names}

Each array item must have exactly these fields:
- name (string)
- country (string)
- description (one sentence, string)
- categories (array of 1-3 strings, only from: Mountains, Beaches, Cities, Culture, Adventure, Nature, Food)
- estimated_budget_inr: MUST be a plain JSON number with no currency symbol,
  currency code, or other text (e.g. 45000.0, never "₹45,000" or "45000 INR")
- best_season (string, e.g. "Oct – Mar")
- duration_days (integer)
"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-3.6-flash",
        generation_config={"response_mime_type": "application/json"},
    )
    response: Any = model.generate_content(prompt)
    try:
        data = json.loads(response.text)
        if not isinstance(data, list):
            raise ValueError("Expected a JSON array of destinations.")
        return [DiscoveredDestinationSchema.model_validate(item) for item in data]
    except (ValidationError, ValueError, TypeError) as exc:
        logger.warning("Discovery response failed schema validation. Raw response: %s", response.text[:2000])
        raise DiscoveryGenerationError("AI returned suggestions that didn't match the required format.") from exc


async def generate_discoveries(user: User) -> list[DiscoveredDestinationSchema]:
    """One real attempt plus one retry on failure — no silent fallback plan;
    callers must surface an error rather than show fabricated content."""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return await asyncio.to_thread(_generate_sync, user)
        except DiscoveryConfigurationError:
            raise
        except DiscoveryGenerationError as exc:
            last_error = exc
            continue
        except Exception as exc:
            last_error = exc
        if attempt == 0:
            await asyncio.sleep(0.5)
    raise DiscoveryGenerationError(str(last_error) if last_error else "AI discovery is temporarily unavailable.")
