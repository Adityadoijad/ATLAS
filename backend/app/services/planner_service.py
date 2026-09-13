"""Structured Gemini trip-plan generation."""
import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.core.prompts import ATLAS_SYSTEM_INSTRUCTION
from app.schemas.planner import GeneratedTripPlanSchema, PlannerRequest

logger = logging.getLogger(__name__)


class PlannerConfigurationError(RuntimeError):
    pass


class PlannerGenerationError(RuntimeError):
    pass


class PlannerValidationError(RuntimeError):
    pass


class PlannerQuotaExceededError(RuntimeError):
    """Gemini's own upstream quota (not ATLAS's app-level rate limit) is
    exhausted. Surfaced immediately — retrying within seconds won't help a
    daily quota, so this skips the transient-retry loop and the caller maps
    it straight to a 429 instead of silently falling back to a stub plan."""


def _default_plan(request: PlannerRequest, *, fallback_reason: str) -> GeneratedTripPlanSchema:
    """Return a bounded, valid structure when Gemini cannot satisfy the schema.

    Marked is_realtime_data=False so callers and the frontend never present this
    placeholder as a genuine AI-generated itinerary.
    """
    return GeneratedTripPlanSchema(
        title=f"{request.destination} travel plan",
        destination=request.destination,
        start_date=request.start_date,
        end_date=request.end_date,
        total_budget=request.budget,
        days=[
            {
                "day_number": 1,
                "date": request.start_date,
                "title": "Flexible arrival day",
                "activities": [
                    {
                        "time": "09:00",
                        "description": "Explore local highlights at your own pace",
                        "location": request.destination,
                        "estimated_cost": 0,
                    }
                ],
            }
        ],
        is_realtime_data=False,
        fallback_reason=fallback_reason,
    )


def _generate_plan_sync(request: PlannerRequest) -> GeneratedTripPlanSchema:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise PlannerConfigurationError("The Gemini SDK is not installed.") from exc

    if not settings.GEMINI_API_KEY:
        raise PlannerConfigurationError("GEMINI_API_KEY is not set.")

    prompt = f"""Create a practical travel plan as JSON only.
Destination: {request.destination}
Start date: {request.start_date.isoformat()}
End date: {request.end_date.isoformat()}
Total budget: {request.budget} {request.currency}
Travellers: {request.travelers}
Preferences: {json.dumps(request.preferences)}

Return an object with title, destination, start_date, end_date, total_budget, and days.
Each day must have day_number, date, title, and activities. Each activity must have
time, description, location, and estimated_cost. Keep dates within the trip range.

CRITICAL: total_budget and every estimated_cost MUST be a plain JSON number
(e.g. 3500.0), never a string, and never containing a currency symbol, currency
code, or any other text. Do NOT include "INR", "Rs", "₹", "$", "USD", commas, or
words of any kind in these fields.
Correct:   "estimated_cost": 3500.0
Incorrect: "estimated_cost": "₹3,500"
Incorrect: "estimated_cost": "3500 INR"
"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-3.6-flash",
        system_instruction=ATLAS_SYSTEM_INSTRUCTION,
        generation_config={"response_mime_type": "application/json"},
    )
    try:
        response: Any = model.generate_content(prompt)
    except Exception as exc:
        from google.api_core.exceptions import ResourceExhausted, TooManyRequests
        if isinstance(exc, (ResourceExhausted, TooManyRequests)):
            raise PlannerQuotaExceededError("Gemini's free-tier quota is exhausted right now.") from exc
        raise
    try:
        return GeneratedTripPlanSchema.model_validate_json(response.text)
    except ValidationError:
        logger.warning("Gemini response failed schema validation. Raw response: %s", response.text[:2000])
        raise


async def generate_trip_plan(request: PlannerRequest) -> GeneratedTripPlanSchema:
    """Generate a validated plan with one schema retry and bounded transient retries."""
    validation_error: ValidationError | None = None
    generation_error: Exception | None = None
    transient_attempts = 0
    validation_attempts = 0
    while transient_attempts < 3 and validation_attempts < 2:
        try:
            return await asyncio.to_thread(_generate_plan_sync, request)
        except PlannerConfigurationError:
            raise
        except PlannerQuotaExceededError:
            raise
        except ValidationError as exc:
            validation_error = exc
            validation_attempts += 1
            if validation_attempts == 2:
                return _default_plan(
                    request,
                    fallback_reason="AI planner returned a response that did not match the required format.",
                )
            await asyncio.sleep(0.25)
            continue
        except Exception as exc:
            generation_error = exc
            transient_attempts += 1
            logger.warning("Gemini generation attempt failed: %s: %s", type(exc).__name__, exc)
            if transient_attempts < 3:
                await asyncio.sleep(0.25 * transient_attempts)

    if validation_error is not None:
        return _default_plan(
            request,
            fallback_reason="AI planner returned a response that did not match the required format.",
        )
    # Preserve the trip-generation flow when the provider is temporarily
    # unavailable; the plan's is_realtime_data=False flag lets the caller and
    # frontend surface the degradation instead of presenting this as a real plan.
    reason = f"{type(generation_error).__name__}: AI planner was temporarily unavailable." if generation_error else "AI planner was temporarily unavailable."
    return _default_plan(request, fallback_reason=reason)
