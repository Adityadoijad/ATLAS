"""Structured AI trip-plan generation (provider-agnostic via ai_service)."""
import asyncio
import json
import logging
from datetime import date, timedelta

from pydantic import ValidationError

from app.core.prompts import ATLAS_SYSTEM_INSTRUCTION
from app.schemas.planner import GeneratedTripPlanSchema, PlannerRequest
from app.services.ai_service import (
    AIConfigurationError,
    AIQuotaExceededError,
    extract_json,
    generate,
)

logger = logging.getLogger(__name__)


class PlannerConfigurationError(RuntimeError):
    pass


class PlannerGenerationError(RuntimeError):
    pass


class PlannerValidationError(RuntimeError):
    pass


class PlannerQuotaExceededError(RuntimeError):
    """The AI provider's own upstream quota (not ATLAS's app-level rate limit) is
    exhausted. Surfaced immediately — retrying within seconds won't help a
    daily quota, so this skips the transient-retry loop and the caller maps
    it straight to a 429 instead of silently falling back to a stub plan."""


def _default_plan(request: PlannerRequest, *, fallback_reason: str) -> GeneratedTripPlanSchema:
    """Return a bounded, valid structure when the AI cannot satisfy the schema.

    Marked is_realtime_data=False so callers and the frontend never present this
    placeholder as a genuine AI-generated itinerary.
    """
    return GeneratedTripPlanSchema(
        title=f"{request.destination} travel plan",
        destination=request.destination,
        start_date=request.start_date,
        end_date=request.end_date,
        total_budget=request.budget,
        # One entry per requested date. A single-day stub would now fail the
        # schema's own coverage rule, and would in any case under-report the
        # trip the traveller asked for.
        days=[
            {
                "day_number": index,
                "date": day,
                "title": "Flexible arrival day" if index == 1 else "Flexible day",
                "activities": [
                    {
                        "time": "09:00",
                        "description": "Explore local highlights at your own pace",
                        "location": request.destination,
                        "estimated_cost": 0,
                        "category": "activity",
                    }
                ],
            }
            for index, day in enumerate(_required_dates(request), start=1)
        ],
        is_realtime_data=False,
        fallback_reason=fallback_reason,
    )


def _boarding_context(request: PlannerRequest) -> str:
    """Tell the planner where the traveller is coming from.

    Deliberately phrased as context, not as a routing instruction. The model is
    good at "they arrive by train from Nagpur, so day one starts at the station
    in the afternoon" and bad at road distances — those come from OSRM after
    the fact. Asking it for kilometres would produce confident invented ones.
    """
    boarding = request.boarding_location
    if boarding is None:
        return ""
    return (
        f"Journey starts from: {boarding.name}\n"
        "Plan the first day around arriving from that starting point rather than "
        "assuming the traveller is already in the destination. Do NOT state distances "
        "or travel times in kilometres or minutes anywhere in the plan.\n"
    )


def itinerary_day_count(start: date, end: date) -> int:
    """How many itinerary days a date range contains.

    Start and end are INCLUSIVE, so the count is the elapsed days plus one:
    Oct 1 -> Oct 1 is 1 day, Oct 1 -> Oct 8 is 8. This is deliberately not the
    same as `(end - start).days`, which counts *nights* and is what the hotel
    agent wants; using it for days is how an eight-day trip became four.
    """
    return (end - start).days + 1


def _required_dates(request: PlannerRequest) -> list[date]:
    return [
        request.start_date + timedelta(days=offset)
        for offset in range(itinerary_day_count(request.start_date, request.end_date))
    ]


def _build_prompt(request: PlannerRequest) -> str:
    required = _required_dates(request)
    date_list = ", ".join(day.isoformat() for day in required)
    return f"""Create a practical travel plan as JSON only.
Destination: {request.destination}
{_boarding_context(request)}Start date: {request.start_date.isoformat()}
End date: {request.end_date.isoformat()}
Total budget: {request.budget} {request.currency}
Travellers: {request.travelers}
Preferences: {json.dumps(request.preferences)}

DURATION — the requested itinerary contains exactly {len(required)} calendar days,
from {request.start_date.isoformat()} through {request.end_date.isoformat()} inclusive.
You MUST return exactly {len(required)} entries in "days", one per date, in this order:
{date_list}
day_number runs 1 to {len(required)} with no gaps and no repeats, and each day's
"date" must be the matching date from that list. Do not return fewer days because
the trip is long, and do not merge or skip days. A plan with any other number of
days is rejected outright.

Return an object with title, destination, start_date, end_date, total_budget, and days.
Each day must have day_number, date, title, and activities. Each activity must have
time, description, location, estimated_cost, and category.

Every activity MUST include exactly one category, as a plain lowercase value
from this list — no other values are accepted:
- "accommodation" = hotel/stay/lodging costs
- "travel" = flights, trains, taxis, buses, transfers, local transport
- "food" = breakfast, lunch, dinner, snacks, restaurants, meals
- "activity" = attractions, tours, sightseeing, entertainment, experiences

Include the real accommodation and meal costs as their own activities so the
budget breakdown reflects the whole trip, not just sightseeing.

LOCATIONS — every "location" value must name a real, identifiable place that
exists on OpenStreetMap. ATLAS looks each one up to compute genuine road
distances and travel times, so an invented name produces no travel information
at all.
- Name an established, specific place: "Jagdish Temple", "Lake Pichola",
  "City Palace", "Udaipur City Railway Station", "Ambrai Restaurant".
- Do NOT invent a restaurant, hotel, cafe, cultural centre, viewpoint or
  attraction. If you cannot confidently name a real business, use a real
  nearby landmark or established place instead, and describe the meal or
  activity in the "description" field.
- Do NOT use generic placeholders as a location: "Traditional Rajasthani
  restaurant", "Local cultural center", "Popular viewpoint", "Hotel terrace",
  "Boutique stay, city centre" are all unusable.
- Do NOT append vague qualifiers to a place name. "near hotel", "near the
  lake", "nearby", "opposite the palace", "city centre" all make the name
  impossible to find. Write "Ambrai Restaurant", never "Ambrai Restaurant,
  near hotel".
- Every place must genuinely be in or around {request.destination}.
- By category: travel -> a real station, airport or bus terminal;
  accommodation -> a real named hotel; food -> a real named restaurant, or
  failing that a real named market, ghat or street known for food;
  activity -> a real named attraction or landmark.
- Do NOT output latitude, longitude, distance or travel time anywhere. ATLAS
  derives those itself from the place names you provide.

CRITICAL: total_budget and every estimated_cost MUST be a plain JSON number
(e.g. 3500.0), never a string, and never containing a currency symbol, currency
code, or any other text. Do NOT include "INR", "Rs", "₹", "$", "USD", commas, or
words of any kind in these fields.
Correct:   "estimated_cost": 3500.0
Incorrect: "estimated_cost": "₹3,500"
Incorrect: "estimated_cost": "3500 INR"
"""


def _repair_note(previous_error: Exception | None, request: PlannerRequest) -> str:
    """What to tell the model about the reply ATLAS just rejected.

    The retry used to re-send a byte-identical prompt, which is a poor way to
    get a different answer: on the trip that surfaced this bug the model
    returned two days for an eight-day range twice in a row. Naming the defect
    costs nothing and gives the retry something to act on.

    This never repairs the plan itself — no day is duplicated or synthesised
    here. It only asks again, more specifically.
    """
    if previous_error is None:
        return ""
    required = itinerary_day_count(request.start_date, request.end_date)
    return (
        "\n\nYOUR PREVIOUS REPLY WAS REJECTED: "
        f"{previous_error}\n"
        f"Return exactly {required} day objects this time, one for each date listed above, "
        "in ascending order. Keep each day brief if that is what it takes to fit them all in.\n"
    )


async def _generate_plan_once(
    request: PlannerRequest, previous_error: Exception | None = None
) -> GeneratedTripPlanSchema:
    try:
        raw = await generate(
            _build_prompt(request) + _repair_note(previous_error, request),
            system_instruction=ATLAS_SYSTEM_INSTRUCTION,
            json_mode=True,
        )
    except AIQuotaExceededError as exc:
        raise PlannerQuotaExceededError(str(exc)) from exc
    except AIConfigurationError as exc:
        raise PlannerConfigurationError(str(exc)) from exc

    try:
        return GeneratedTripPlanSchema.model_validate(extract_json(raw))
    except (ValidationError, ValueError):
        # Both mean the same thing operationally: the model produced output
        # ATLAS can't trust. The caller retries once, then falls back to a
        # clearly-labelled placeholder rather than inventing an itinerary.
        logger.warning("AI response failed schema validation. Raw response: %s", raw[:2000])
        raise


async def generate_trip_plan(request: PlannerRequest) -> GeneratedTripPlanSchema:
    """Generate a validated plan with one schema retry and bounded transient retries."""
    validation_error: Exception | None = None
    generation_error: Exception | None = None
    transient_attempts = 0
    validation_attempts = 0
    while transient_attempts < 3 and validation_attempts < 2:
        try:
            return await _generate_plan_once(request, validation_error)
        except PlannerConfigurationError:
            raise
        except PlannerQuotaExceededError:
            raise
        except (ValidationError, ValueError) as exc:
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
            logger.warning("AI generation attempt failed: %s: %s", type(exc).__name__, exc)
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
