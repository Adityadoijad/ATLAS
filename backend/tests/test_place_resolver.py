"""Verifying that the planner named real places.

The invariant under test is narrow and important: a location the geocoder
cannot find is left alone. Not replaced by the destination centre, not given a
coordinate, not quietly dropped. Repair may only *narrow* a name — never swap
one real place for a different one — and a repair that lands on a containing
landmark is recorded as approximate rather than passed off as exact.

Nominatim is mocked throughout.
"""
import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema
from app.services import place_resolver
from app.services.integrations.maps import GeocodingUnavailable
from app.services.place_resolver import (
    MAX_LOOKUPS,
    plan_locations,
    repair_candidates,
    verify_plan_locations,
)

# Places that exist in OpenStreetMap around Udaipur.
REAL_PLACES = {
    "city palace, udaipur",
    "lake pichola, udaipur",
    "jagdish temple, udaipur",
    "udaipur city railway station",
    "nagpur railway station",
    "ambrai restaurant, udaipur",
    "saheliyon-ki-bari, udaipur",
    "fateh sagar lake, udaipur",
    "ambrai ghat, udaipur",
}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def geocoder(monkeypatch):
    """Resolves only the names in REAL_PLACES; records every query made."""
    queries: list[str] = []

    async def fake_geocode_place(query: str):
        queries.append(query)
        if query.strip().casefold() in REAL_PLACES:
            return {
                "name": query,
                "display_name": f"{query}, India",
                "latitude": 24.5854,
                "longitude": 73.7125,
            }
        return None

    monkeypatch.setattr(place_resolver, "geocode_place", fake_geocode_place)
    return queries


def _plan(*locations: str, destination: str = "Udaipur") -> GeneratedTripPlanSchema:
    return GeneratedTripPlanSchema(
        title="Trip",
        destination=destination,
        # One day, so the range is one date. These tests are about place
        # names, not duration; declaring a two-day range with a single day
        # would now (correctly) fail schema validation.
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 10),
        total_budget=30000,
        days=[DayPlanSchema(
            day_number=1,
            date=date(2026, 12, 10),
            title="Day 1",
            activities=[
                ActivitySchema(
                    time=f"{9 + index:02d}:00",
                    description="Visit",
                    location=location,
                    estimated_cost=100,
                    category="activity",
                )
                for index, location in enumerate(locations)
            ],
        )],
    )


# --------------------------------------------------------------------------
# Repair candidates: narrowing only, never substitution
# --------------------------------------------------------------------------

def test_a_clean_real_name_needs_no_repair() -> None:
    assert repair_candidates("Jagdish Temple") == [("Jagdish Temple", False)]


def test_a_vague_qualifier_after_a_comma_is_dropped() -> None:
    names = [name for name, _ in repair_candidates("Mitra Restaurant, near hotel")]
    assert "Mitra Restaurant" in names
    # The original is still tried first — it might genuinely be the full name.
    assert names[0] == "Mitra Restaurant, near hotel"


def test_a_vague_qualifier_without_a_comma_is_dropped() -> None:
    names = [name for name, _ in repair_candidates("Ambrai Restaurant near hotel")]
    assert "Ambrai Restaurant" in names


def test_a_parenthetical_aside_is_dropped() -> None:
    names = [name for name, _ in repair_candidates("City Palace (entry tickets)")]
    assert "City Palace" in names


def test_stepping_back_to_a_containing_landmark_is_marked_approximate() -> None:
    """"Lake Pichola jetty" -> "Lake Pichola" is the same spot, not the same thing."""
    candidates = repair_candidates("Lake Pichola jetty")
    approximate = [name for name, is_approx in candidates if is_approx]
    assert approximate == ["Lake Pichola"]


def test_every_candidate_narrows_the_original_rather_than_replacing_it() -> None:
    """The safety property: repair can never name a different place."""
    for original in (
        "Ambrai Ghat Café",
        "Mitra Restaurant, near hotel",
        "City Palace (entry tickets)",
        "Hotel Lake Palace, Lake Pichola",
    ):
        first_word = original.split()[0].casefold()
        for name, _ in repair_candidates(original):
            assert name.casefold().startswith(first_word), (
                f"repair of {original!r} produced {name!r}, which names something else"
            )


@pytest.mark.parametrize(
    "generic",
    [
        "Traditional Rajasthani restaurant",
        "Local cultural center",
        "Popular viewpoint",
        "Hotel terrace",
        "local food market",
        "the city centre",
    ],
)
def test_a_purely_descriptive_name_is_still_tried_then_left_unresolved(generic: str, geocoder) -> None:
    """Whether a name is real is Nominatim's call, not a word list's.

    These are tried once and fail, which is the honest outcome. Refusing to
    look them up would mean classifying names lexically, and that same
    classifier would reject "City Palace".
    """
    plan = _plan(generic)
    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.resolved == 0
    assert report.unresolved_names == [generic]
    assert plan_locations(plan) == [generic]


def test_a_real_name_made_of_ordinary_words_is_looked_up(geocoder) -> None:
    """Regression: an earlier word list called "City Palace" generic and
    skipped it, which manufactured the very unresolved locations this work
    exists to remove."""
    assert repair_candidates("City Palace")[0] == ("City Palace", False)
    assert repair_candidates("Fateh Sagar Lake")[0] == ("Fateh Sagar Lake", False)

    plan = _plan("City Palace", "Fateh Sagar Lake")
    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))
    assert report.resolved == 2


def test_a_trim_never_collapses_a_name_to_a_single_common_word() -> None:
    """"Mitra Restaurant" must not become "Mitra", which could match anything."""
    names = [name for name, _ in repair_candidates("Mitra Restaurant, near hotel")]
    assert "Mitra" not in names
    assert "Mitra Restaurant" in names


# --------------------------------------------------------------------------
# Verifying a whole plan
# --------------------------------------------------------------------------

def test_real_places_resolve_and_are_left_untouched(geocoder) -> None:
    plan = _plan("City Palace", "Lake Pichola", "Jagdish Temple", "Udaipur City Railway Station")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.total == 4
    assert report.resolved == 4
    assert report.resolution_rate == 1.0
    assert report.repaired == {}
    assert plan_locations(plan) == [
        "City Palace", "Lake Pichola", "Jagdish Temple", "Udaipur City Railway Station"
    ]


def test_a_repairable_name_is_rewritten_in_the_plan(geocoder) -> None:
    """The traveller should see the name ATLAS can actually find."""
    plan = _plan("Ambrai Restaurant, near hotel")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.resolved == 1
    assert report.repaired == {"Ambrai Restaurant, near hotel": "Ambrai Restaurant"}
    assert plan_locations(plan) == ["Ambrai Restaurant"]


def test_an_approximate_repair_is_recorded_as_approximate(geocoder) -> None:
    plan = _plan("Ambrai Ghat Café")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.resolved == 1
    assert plan_locations(plan) == ["Ambrai Ghat"]
    assert report.approximate_names == ["Ambrai Ghat Café"]


def test_an_unresolvable_name_is_left_exactly_as_written(geocoder) -> None:
    """The core invariant: no coordinate, no substitute, no silent edit."""
    plan = _plan("Mitra Restaurant", "Udaipur Cultural Center")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.resolved == 0
    assert sorted(report.unresolved_names) == ["Mitra Restaurant", "Udaipur Cultural Center"]
    # Unchanged in the plan.
    assert plan_locations(plan) == ["Mitra Restaurant", "Udaipur Cultural Center"]


def test_an_unresolvable_name_is_never_replaced_by_the_destination(geocoder) -> None:
    plan = _plan("Udaipur Cultural Center")
    asyncio.run(verify_plan_locations(plan, "Udaipur"))
    assert plan_locations(plan) == ["Udaipur Cultural Center"]
    assert "Udaipur" != plan.days[0].activities[0].location


def test_the_plan_never_gains_coordinates(geocoder) -> None:
    """Locations stay names; the route service owns turning them into points."""
    plan = _plan("City Palace")
    asyncio.run(verify_plan_locations(plan, "Udaipur"))

    activity = plan.days[0].activities[0]
    assert not hasattr(activity, "latitude")
    assert not hasattr(activity, "longitude")
    assert activity.location == "City Palace"


def test_the_resolution_rate_is_reported(geocoder) -> None:
    plan = _plan("City Palace", "Lake Pichola", "Mitra Restaurant", "Udaipur Cultural Center")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.total == 4
    assert report.resolved == 2
    assert report.resolution_rate == 0.5
    assert report.as_dict()["place_resolution_rate"] == 0.5


def test_an_empty_plan_reports_no_rate_rather_than_zero() -> None:
    """0/0 is not 0% — there was nothing to judge."""
    report = place_resolver.ResolutionReport()
    assert report.resolution_rate is None


# --------------------------------------------------------------------------
# Geocoder budget
# --------------------------------------------------------------------------

def test_a_repeated_location_is_looked_up_once(geocoder) -> None:
    """A trip returning to the same hotel four times is one lookup."""
    plan = _plan("City Palace", "City Palace", "City Palace", "Lake Pichola")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.total == 2, "distinct names only"
    assert geocoder.count("City Palace, Udaipur") == 1


def test_a_descriptive_name_costs_few_lookups_and_resolves_nothing(geocoder) -> None:
    plan = _plan("Traditional Rajasthani restaurant", "City Palace")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    # Bounded: the original plus at most one narrowing attempt.
    assert len([q for q in geocoder if "Rajasthani" in q]) <= 2
    assert "Traditional Rajasthani restaurant" in report.unresolved_names


def test_repair_stops_at_the_first_name_that_resolves(geocoder) -> None:
    """No further lookups once something works."""
    plan = _plan("City Palace")
    asyncio.run(verify_plan_locations(plan, "Udaipur"))
    assert geocoder == ["City Palace, Udaipur"]


def test_lookups_are_capped(geocoder) -> None:
    plan = _plan(*[f"Place Number {index}" for index in range(MAX_LOOKUPS + 8)])

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.total == MAX_LOOKUPS
    # Names past the cap are left unverified, not declared bad.
    assert len(report.unresolved_names) <= MAX_LOOKUPS


def test_a_name_already_naming_the_city_is_not_doubled_up(geocoder) -> None:
    plan = _plan("Udaipur City Railway Station")
    asyncio.run(verify_plan_locations(plan, "Udaipur"))
    assert geocoder == ["Udaipur City Railway Station"]


# --------------------------------------------------------------------------
# Geocoder outage
# --------------------------------------------------------------------------

def test_an_unreachable_geocoder_leaves_the_plan_untouched(monkeypatch) -> None:
    """"We could not check" is not "the names are wrong"."""
    async def unavailable(query: str):
        raise GeocodingUnavailable("The location service could not be reached.")

    monkeypatch.setattr(place_resolver, "geocode_place", unavailable)
    plan = _plan("Ambrai Restaurant, near hotel", "City Palace")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur"))

    assert report.geocoder_unavailable is True
    assert report.unresolved_names == []
    assert plan_locations(plan) == ["Ambrai Restaurant, near hotel", "City Palace"]


def test_verification_never_raises(monkeypatch) -> None:
    """Trip generation must not fail because the geocoder had a bad minute."""
    async def unavailable(query: str):
        raise GeocodingUnavailable("down")

    monkeypatch.setattr(place_resolver, "geocode_place", unavailable)
    asyncio.run(verify_plan_locations(_plan("Anywhere At All"), "Udaipur"))


# --------------------------------------------------------------------------
# Endpoint integration
# --------------------------------------------------------------------------

def test_the_trip_records_its_place_resolution(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    from tests.test_planner import fake_generate_trip_plan

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate_trip_plan)

    async def fake_geocode_place(query: str):
        return None if "Candolim" in query else {
            "name": query, "display_name": query, "latitude": 15.5, "longitude": 73.8,
        }

    monkeypatch.setattr(place_resolver, "geocode_place", fake_geocode_place)

    response = client.post(
        "/api/trips/generate",
        json={
            "destination": "Goa", "start_date": "2026-12-10", "end_date": "2026-12-11",
            "budget": 25000, "boarding_location": {"name": "Nagpur Railway Station"},
        },
        headers=auth(user_a_token),
    )

    assert response.status_code == 201, response.text
    places = response.json()["data_context"]["places"]
    assert places["total_locations"] == 2
    assert places["resolved_locations"] == 1
    assert places["place_resolution_rate"] == 0.5
    assert places["unresolved_locations"] == ["Candolim"]


def test_place_metadata_is_internal_not_a_user_facing_score(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    """It lives in data_context alongside the other provenance flags, not as a
    headline number on the trip."""
    from tests.test_planner import fake_generate_trip_plan

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate_trip_plan)

    async def fake_geocode_place(query: str):
        return {"name": query, "display_name": query, "latitude": 15.5, "longitude": 73.8}

    monkeypatch.setattr(place_resolver, "geocode_place", fake_geocode_place)

    body = client.post(
        "/api/trips/generate",
        json={
            "destination": "Goa", "start_date": "2026-12-10", "end_date": "2026-12-11",
            "budget": 25000, "boarding_location": {"name": "Nagpur Railway Station"},
        },
        headers=auth(user_a_token),
    ).json()

    assert "places" in body["data_context"]
    assert "place_resolution_rate" not in body


def test_the_prompt_demands_real_places() -> None:
    from app.schemas.planner import PlannerRequest
    from app.services.planner_service import _build_prompt

    prompt = _build_prompt(PlannerRequest(
        destination="Udaipur",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 12),
        budget=30000,
    ))

    assert "OpenStreetMap" in prompt
    assert "Do NOT invent" in prompt
    assert "near hotel" in prompt
    # And it still forbids the model inventing the numbers ATLAS derives.
    assert "Do NOT output latitude, longitude, distance or travel time" in prompt


def test_the_boarding_location_is_not_qualified_with_the_destination(geocoder) -> None:
    """Regression, found on a real generated trip.

    The departure point is somewhere else entirely, so appending the
    destination produced "Nagpur Railway Station, Udaipur" — a place that does
    not exist. It was then reported as an unresolved location, understating the
    resolution rate and wasting a lookup on a question with no answer.
    """
    plan = _plan("Nagpur Railway Station", "City Palace")

    report = asyncio.run(verify_plan_locations(plan, "Udaipur", "Nagpur Railway Station"))

    assert "Nagpur Railway Station, Udaipur" not in geocoder
    assert "Nagpur Railway Station" in geocoder
    # It is in REAL_PLACES unqualified, so it now resolves.
    assert report.resolved == 2
    assert report.unresolved_names == []


def test_other_locations_are_still_qualified_when_a_boarding_name_is_given(geocoder) -> None:
    plan = _plan("City Palace")
    asyncio.run(verify_plan_locations(plan, "Udaipur", "Nagpur Railway Station"))
    assert geocoder == ["City Palace, Udaipur"]
