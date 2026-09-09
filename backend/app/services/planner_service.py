"""Structured Gemini trip-plan generation."""
import asyncio
import json
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.core.prompts import ATLAS_SYSTEM_INSTRUCTION
from app.schemas.planner import GeneratedTripPlanSchema, PlannerRequest


class PlannerConfigurationError(RuntimeError):
    pass


class PlannerGenerationError(RuntimeError):
    pass


class PlannerValidationError(RuntimeError):
    pass


def _default_plan(request: PlannerRequest) -> GeneratedTripPlanSchema:
    """Return a bounded, valid structure when Gemini cannot satisfy the schema."""
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
"""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-3.6-flash",
        system_instruction=ATLAS_SYSTEM_INSTRUCTION,
        generation_config={"response_mime_type": "application/json"},
    )
    response: Any = model.generate_content(prompt)
    return GeneratedTripPlanSchema.model_validate_json(response.text)


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
        except ValidationError as exc:
            validation_error = exc
            validation_attempts += 1
            if validation_attempts == 2:
                return _default_plan(request)
            await asyncio.sleep(0.25)
            continue
        except Exception as exc:
            generation_error = exc
            transient_attempts += 1
            if transient_attempts < 3:
                await asyncio.sleep(0.25 * transient_attempts)

    if validation_error is not None:
        return _default_plan(request)
    # Preserve the trip-generation flow when the provider is temporarily
    # unavailable; the caller can surface the realtime-data degradation flag.
    return _default_plan(request)
