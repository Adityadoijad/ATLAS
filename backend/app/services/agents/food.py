"""Food agent: live eating places from OpenStreetMap, with the previous
budget-share estimate kept as the fallback.

Two different claims live in this agent's output and must not be conflated:

  * where to eat  — live OSM data when Overpass answers (is_realtime_data)
  * what it costs — always an estimate; OSM has no reliable menu prices
                    (cost_is_estimated is therefore always True)

Reporting the second as live would be a lie, so the flags stay separate and
the UI phrases them separately.
"""
import logging

from app.schemas.planner import PlannerRequest
from app.services.integrations.maps import geocode_destination
from app.services.integrations.overpass import (
    DEFAULT_RADIUS_M,
    OverpassRateLimited,
    get_food_places,
)

logger = logging.getLogger(__name__)

# How many places to carry into the itinerary context. Enough to cover a
# multi-day trip's meals without bloating every planner response.
_MAX_PLACES = 12

# Share of the trip budget set aside for meals — the original estimate, kept
# because Overpass tells us where to eat but never what it costs.
_MEAL_BUDGET_SHARE = 0.16

# Diet preferences that map onto OSM's own cuisine vocabulary. Only these can
# be matched honestly; anything else the traveller asked for is left to the
# planner prompt rather than guessed at from a venue name.
_PREFERENCE_CUISINE_HINTS = {
    "vegetarian": ("vegetarian",),
    "vegan": ("vegan",),
    "local cuisine": ("indian", "regional", "local"),
    "street food": ("street_food", "fast food"),
    "fine dining": ("fine_dining",),
    "seafood": ("seafood",),
}

# Alcohol-led venues are only searched when the traveller actually asked for
# nightlife, so a family trip's suggestions are not led by pubs and bars.
_BAR_PREFERENCES = {"nightlife", "bars", "pubs"}


def _estimate_fallback(request: PlannerRequest, reason: str) -> dict[str, object]:
    """The pre-Overpass behaviour, unchanged, plus an honest reason."""
    preferences = request.preferences.get("food", [])
    preference_text = ", ".join(str(item) for item in preferences) or "local cuisine"
    return {
        "is_realtime_data": False,
        "cost_is_estimated": True,
        "recommendation": (
            f"Prioritise {preference_text} and reserve roughly "
            f"{int(_MEAL_BUDGET_SHARE * 100)}% of the budget for meals."
        ),
        "fallback_reason": reason,
    }


def _wanted_cuisines(preferences: list[str]) -> set[str]:
    hints: set[str] = set()
    for preference in preferences:
        hints.update(_PREFERENCE_CUISINE_HINTS.get(str(preference).strip().lower(), ()))
    return hints


def _rank(places: list[dict[str, object]], wanted_cuisines: set[str]) -> list[dict[str, object]]:
    """Order places by how well they match the traveller, then by how much OSM
    actually knows about them.

    Ranking only ever reorders — a place is never dropped for failing to match
    a preference, because OSM's cuisine tag is sparse and absence of the tag is
    not evidence the food is wrong.
    """
    def score(place: dict[str, object]) -> tuple[int, int, int]:
        cuisine = str(place.get("cuisine") or "").casefold()
        matches_preference = int(bool(wanted_cuisines) and any(hint in cuisine for hint in wanted_cuisines))
        # Sit-down restaurants and cafes before fast food for meal planning.
        is_proper_venue = int(place.get("category") in ("restaurant", "cafe", "food_court"))
        detail = sum(1 for field in ("cuisine", "address", "opening_hours", "website", "phone") if place.get(field))
        return (matches_preference, is_proper_venue, detail)

    return sorted(places, key=score, reverse=True)


class FoodAgent:
    name = "food"
    # Overpass is slower than the other integrations, so this agent gets a
    # longer leash than the 2.5s default. It still finishes well inside the
    # AI plan generation it runs concurrently with, so the planner's overall
    # latency is unchanged.
    timeout_seconds = 14.0

    async def run(self, request: PlannerRequest) -> dict[str, object]:
        preferences = [str(item) for item in request.preferences.get("food", [])]
        interests = {str(item).strip().lower() for item in request.preferences.get("interests", [])}

        try:
            coordinates = await geocode_destination(request.destination)
        except Exception as exc:
            logger.warning(
                "Food agent could not geocode %r: %s", request.destination, type(exc).__name__
            )
            return _estimate_fallback(
                request, f"{request.destination} could not be located, so live food data was unavailable."
            )

        try:
            places = await get_food_places(
                coordinates["latitude"],
                coordinates["longitude"],
                radius_m=DEFAULT_RADIUS_M,
                include_bars=bool(interests & _BAR_PREFERENCES),
            )
        except OverpassRateLimited:
            return _estimate_fallback(
                request, "OpenStreetMap Overpass is rate limited right now, so meal guidance is estimated."
            )
        except Exception as exc:
            logger.warning(
                "Food agent Overpass lookup failed for %r: %s", request.destination, type(exc).__name__
            )
            return _estimate_fallback(
                request, "OpenStreetMap Overpass could not be reached, so meal guidance is estimated."
            )

        if not places:
            return _estimate_fallback(
                request,
                "OpenStreetMap Overpass returned no usable restaurant data for this destination.",
            )

        ranked = _rank(places, _wanted_cuisines(preferences))[:_MAX_PLACES]
        preference_text = ", ".join(preferences) or "local cuisine"
        return {
            "is_realtime_data": True,
            # Places are live; the money is not. The UI relies on this staying
            # true even on the success path.
            "cost_is_estimated": True,
            "places": ranked,
            "place_count": len(places),
            "source": "openstreetmap",
            "attribution": "Food place data © OpenStreetMap contributors",
            "recommendation": (
                f"{len(places)} food places found near {request.destination} on OpenStreetMap. "
                f"Prioritise {preference_text}; budget roughly "
                f"{int(_MEAL_BUDGET_SHARE * 100)}% of the trip for meals (estimated — "
                "OpenStreetMap does not publish prices)."
            ),
        }
