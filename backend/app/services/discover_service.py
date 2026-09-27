"""AI-generated ("Discover more") destination suggestions — on-demand, real
AI calls, distinct from the fast catalog-based recommendations in
recommendations.py. Slower and quota-bound like the trip planner, so this is
opt-in behind its own endpoint rather than loaded automatically on every page
view.

No silent fallback: if the model can't produce valid suggestions, this raises
rather than fabricating fake "AI discoveries" — matching the same honesty
requirement enforced in planner_service.py.
"""
import asyncio
import logging

from pydantic import ValidationError

from app.models.user import User
from app.schemas.recommendations import DiscoveredDestinationSchema
from app.services.ai_service import (
    AIConfigurationError,
    AIQuotaExceededError,
    extract_json,
    generate,
)
from app.services.integrations.photos import attach_photos
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


async def _generate_once(user: User) -> list[DiscoveredDestinationSchema]:
    exclude_names = ", ".join(str(item["name"]) for item in CATALOG)
    # JSON mode guarantees an object at the root, so the array is requested
    # under a single key and unwrapped below.
    prompt = f"""Suggest exactly 3 real, existing travel destinations for a traveller
booking from India, as JSON. Return an object with a single key "destinations"
whose value is an array of exactly 3 items.

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
    try:
        raw = await generate(prompt, json_mode=True, max_tokens=2000)
    except AIConfigurationError as exc:
        raise DiscoveryConfigurationError(str(exc)) from exc
    except AIQuotaExceededError as exc:
        raise DiscoveryGenerationError(str(exc)) from exc

    try:
        data = extract_json(raw)
        # Accept either the requested {"destinations": [...]} wrapper or a
        # bare array, so a well-formed response isn't rejected on shape alone.
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), None)
        if not isinstance(data, list):
            raise ValueError("Expected an array of destinations.")
        return [DiscoveredDestinationSchema.model_validate(item) for item in data]
    except (ValidationError, ValueError, TypeError) as exc:
        logger.warning("Discovery response failed schema validation. Raw response: %s", raw[:2000])
        raise DiscoveryGenerationError("AI returned suggestions that didn't match the required format.") from exc


async def _with_photos(
    destinations: list[DiscoveredDestinationSchema],
) -> list[DiscoveredDestinationSchema]:
    """Attach a real photo of each suggested place.

    Looked up after generation rather than asked of the model, because a model
    asked for an image URL will confidently invent one that 404s. A lookup that
    finds nothing leaves image_url as None.
    """
    photos = await attach_photos([(item.name, item.country) for item in destinations])
    for item, photo in zip(destinations, photos):
        item.image_url = photo
    return destinations


async def generate_discoveries(user: User) -> list[DiscoveredDestinationSchema]:
    """One real attempt plus one retry on failure — no silent fallback plan;
    callers must surface an error rather than show fabricated content."""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return await _with_photos(await _generate_once(user))
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
