"""Boarding location, route sequencing, and real travel distance/time.

The single assertion running through this file: **a missing leg is null, never
zero.** Zero is a real answer meaning two stops are the same place. Using it
for "we could not find out" turns a provider outage into a confident claim
that a journey takes no time at all, which is the bug this whole feature set
exists to remove.

Every provider is mocked. Nothing here calls Nominatim or OSRM.
"""
import asyncio
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from app.models.itinerary import ItineraryDay
from app.models.trip import Trip
from app.schemas.planner import BoardingLocation, PlannerRequest
from app.services import route_sequence
from app.services.integrations import maps as maps_module
from app.services.integrations import routing as routing_module
from app.services.integrations.routing import (
    RouteLeg,
    RoutingUnavailable,
    get_route_legs,
)
from app.services.route_sequence import build_sequence, itinerary_locations, resolve_sequence

NAGPUR = (21.1458, 79.0882)
UDAIPUR_STATION = (24.5854, 73.7125)
FATEH_SAGAR = (24.6000, 73.6800)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset_routing_state():
    def clear():
        routing_module._cache.clear()
        routing_module._inflight.clear()
        routing_module.routing_breaker.failures = 0
        routing_module.routing_breaker.opened_at = None
        maps_module._place_cache.clear()
        maps_module.maps_breaker.failures = 0
        maps_module.maps_breaker.opened_at = None

    clear()
    yield
    clear()


@pytest.fixture(autouse=True)
def _no_geocoder_throttle(monkeypatch):
    """Nominatim's one-per-second pacing is real but would crawl the suite."""
    async def instant():
        return None

    monkeypatch.setattr(maps_module, "_throttle", instant)


def _osrm_payload(*legs: tuple[float, float]):
    """legs as (metres, seconds)."""
    return {
        "code": "Ok",
        "routes": [{"legs": [{"distance": d, "duration": t} for d, t in legs]}],
    }


def _responder(payload, status: int = 200):
    calls: list[str] = []

    async def fake_get(self, url, params=None):
        calls.append(str(url))
        return httpx.Response(status, json=payload, request=httpx.Request("GET", url))

    return fake_get, calls


# --------------------------------------------------------------------------
# OSRM integration
# --------------------------------------------------------------------------

def test_consecutive_legs_are_returned_in_order(monkeypatch) -> None:
    fake_get, calls = _responder(_osrm_payload((3800, 840), (4500, 540)))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    legs = asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION, FATEH_SAGAR]))

    assert [(leg.from_index, leg.to_index) for leg in legs] == [(0, 1), (1, 2)]
    assert legs[0].distance_km == 3.8
    assert legs[0].duration_minutes == 14
    assert legs[1].distance_km == 4.5
    assert legs[1].duration_minutes == 9
    assert all(leg.routing_available for leg in legs)
    # One request for the whole sequence, not one per pair.
    assert len(calls) == 1


def test_coordinates_are_sent_as_lon_lat(monkeypatch) -> None:
    """OSRM reverses the order every other ATLAS integration uses.

    Getting this backwards does not error — it silently routes between two
    entirely different places and returns a plausible number.
    """
    fake_get, calls = _responder(_osrm_payload((1000, 120)))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION]))

    assert "79.0882,21.1458;73.7125,24.5854" in calls[0]


def test_a_single_stop_has_no_legs(monkeypatch) -> None:
    called = False

    async def fake_get(self, url, params=None):
        nonlocal called
        called = True
        return httpx.Response(200, json={}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert asyncio.run(get_route_legs([NAGPUR])) == []
    assert called is False, "a trip with one stop needs no routing request"


@pytest.mark.parametrize("status", [429, 500, 503])
def test_provider_errors_raise_rather_than_returning_zero(monkeypatch, status: int) -> None:
    fake_get, _ = _responder({}, status=status)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(RoutingUnavailable):
        asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION]))


def test_no_route_is_reported_as_unavailable_not_as_zero_distance(monkeypatch) -> None:
    """An unreachable stop must not read as "already there"."""
    fake_get, _ = _responder({"code": "NoRoute", "routes": []})
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(RoutingUnavailable) as raised:
        asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION]))
    assert "No drivable route" in str(raised.value)


def test_a_network_failure_never_leaks_the_request_url(monkeypatch) -> None:
    async def fake_get(self, url, params=None):
        raise httpx.ConnectTimeout("timed out", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(RoutingUnavailable) as raised:
        asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION]))
    assert "router.project-osrm.org" not in str(raised.value)


def test_a_leg_with_unusable_numbers_is_null_not_zero(monkeypatch) -> None:
    fake_get, _ = _responder({
        "code": "Ok",
        "routes": [{"legs": [{"distance": None, "duration": None}, {"distance": 4500, "duration": 540}]}],
    })
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    legs = asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION, FATEH_SAGAR]))

    assert legs[0].distance_km is None
    assert legs[0].duration_minutes is None
    assert legs[0].routing_available is False
    # One bad leg does not discard the good one beside it.
    assert legs[1].distance_km == 4.5


def test_a_mismatched_leg_count_is_refused_rather_than_misaligned(monkeypatch) -> None:
    """A distance attached to the wrong pair is worse than no distance."""
    fake_get, _ = _responder(_osrm_payload((3800, 840)))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(RoutingUnavailable):
        asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION, FATEH_SAGAR]))


def test_a_repeat_route_is_served_from_cache(monkeypatch) -> None:
    fake_get, calls = _responder(_osrm_payload((3800, 840)))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    first = asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION]))
    second = asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION]))

    assert first == second
    assert len(calls) == 1


def test_a_failure_is_not_cached_as_a_successful_route(monkeypatch) -> None:
    state = {"fail": True}

    async def fake_get(self, url, params=None):
        if state["fail"]:
            return httpx.Response(500, json={}, request=httpx.Request("GET", url))
        return httpx.Response(200, json=_osrm_payload((3800, 840)), request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(RoutingUnavailable):
        asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION]))
    assert routing_module._cache == {}

    state["fail"] = False
    routing_module.routing_breaker.failures = 0
    routing_module.routing_breaker.opened_at = None
    assert asyncio.run(get_route_legs([NAGPUR, UDAIPUR_STATION]))[0].distance_km == 3.8


def test_route_leg_never_reports_zero_as_available_when_unknown() -> None:
    unknown = RouteLeg(0, 1, None, None)
    assert unknown.routing_available is False
    assert unknown.as_dict()["distance_km"] is None
    assert unknown.as_dict()["distance_km"] != 0


# --------------------------------------------------------------------------
# The canonical sequence
# --------------------------------------------------------------------------

def _trip(boarding: dict | None = None, destination: str = "Udaipur") -> Trip:
    trip = Trip(destination=destination, boarding_location=boarding)
    trip.itinerary_days = [
        ItineraryDay(
            day_number=1,
            description=(
                "09:00 | Arrive | Udaipur City Railway Station | 0 | travel\n"
                "11:00 | Check in | Lake City Heritage Hotel | 4000 | accommodation\n"
                "16:00 | Sunset | Fateh Sagar Lake | 200 | activity"
            ),
        ),
        ItineraryDay(
            day_number=2,
            description="09:00 | Breakfast | Lake City Heritage Hotel | 300 | food",
        ),
    ]
    return trip


def test_locations_are_read_from_the_pipe_delimited_itinerary() -> None:
    assert itinerary_locations(_trip()) == [
        "Udaipur City Railway Station",
        "Lake City Heritage Hotel",
        "Fateh Sagar Lake",
        "Lake City Heritage Hotel",
    ]


def test_rows_written_before_the_category_field_still_parse() -> None:
    trip = Trip(destination="Goa", boarding_location=None)
    trip.itinerary_days = [ItineraryDay(day_number=1, description="09:00 | Arrive | Panaji | 0")]
    assert itinerary_locations(trip) == ["Panaji"]


def test_the_boarding_location_is_the_first_stop() -> None:
    """The acceptance criterion: the route originates where the user departs."""
    trip = _trip({"name": "Nagpur Railway Station", "latitude": 21.1458, "longitude": 79.0882})
    stops = build_sequence(trip)

    assert stops[0].label == "Nagpur Railway Station"
    assert stops[0].is_boarding is True
    assert stops[1].label == "Udaipur City Railway Station"
    assert stops[1].is_boarding is False


def test_a_trip_without_a_boarding_location_starts_at_its_first_stop() -> None:
    """Backward compatibility: old trips are not given an invented origin."""
    stops = build_sequence(_trip(None))

    assert stops[0].label == "Udaipur City Railway Station"
    assert not any(stop.is_boarding for stop in stops)


def test_stops_are_qualified_with_the_destination_city() -> None:
    """'Fateh Sagar Lake' alone is ambiguous to a worldwide geocoder."""
    stops = build_sequence(_trip(None))
    lake = next(stop for stop in stops if stop.label == "Fateh Sagar Lake")

    assert lake.query == "Fateh Sagar Lake, Udaipur"
    # A stop that already names the city is not doubled up.
    station = next(stop for stop in stops if "Railway Station" in stop.label)
    assert station.query == "Udaipur City Railway Station"


def test_a_consecutive_repeat_collapses_but_a_return_visit_does_not() -> None:
    """The hotel is one place to drive to on day one, and a real return on day two."""
    labels = [stop.label for stop in build_sequence(_trip(None))]
    assert labels == [
        "Udaipur City Railway Station",
        "Lake City Heritage Hotel",
        "Fateh Sagar Lake",
        "Lake City Heritage Hotel",
    ]


def test_the_sequence_is_capped() -> None:
    trip = Trip(destination="Goa", boarding_location=None)
    trip.itinerary_days = [ItineraryDay(
        day_number=1,
        description="\n".join(f"09:00 | Stop | Place {i} | 0 | activity" for i in range(40)),
    )]
    assert len(build_sequence(trip)) == route_sequence.MAX_SEQUENCE_STOPS


# --------------------------------------------------------------------------
# Sequence + routing together
# --------------------------------------------------------------------------

def _stub_geocoder(monkeypatch, coordinates: dict[str, tuple[float, float]]):
    async def fake_geocode_places(queries):
        results = []
        for query in queries:
            match = coordinates.get(query)
            results.append(
                None if match is None
                else {"name": query, "display_name": query, "latitude": match[0], "longitude": match[1]}
            )
        return results

    monkeypatch.setattr(route_sequence, "geocode_places", fake_geocode_places)


def test_the_first_leg_runs_from_the_boarding_location(monkeypatch) -> None:
    """A -> B, never B -> B and never destination-centre -> B."""
    trip = _trip({"name": "Nagpur Railway Station", "latitude": 21.1458, "longitude": 79.0882})
    _stub_geocoder(monkeypatch, {
        "Udaipur City Railway Station": UDAIPUR_STATION,
        "Lake City Heritage Hotel, Udaipur": (24.5800, 73.6900),
        "Fateh Sagar Lake, Udaipur": FATEH_SAGAR,
    })

    requested: list[list[tuple[float, float]]] = []

    async def fake_get_route_legs(coordinates):
        requested.append(list(coordinates))
        return [RouteLeg(i, i + 1, 10.0, 20) for i in range(len(coordinates) - 1)]

    monkeypatch.setattr(route_sequence, "get_route_legs", fake_get_route_legs)

    stops, legs, reason = asyncio.run(resolve_sequence(trip))

    assert reason is None
    # The very first coordinate sent to the router is where the user boards.
    assert requested[0][0] == NAGPUR
    assert requested[0][1] == UDAIPUR_STATION
    assert stops[0].is_boarding is True
    assert legs[0].from_index == 0 and legs[0].to_index == 1


def test_the_stored_boarding_coordinates_are_reused_not_re_geocoded(monkeypatch) -> None:
    """They are what the user confirmed; a geocoder that changed its mind must
    not silently relocate the trip's origin."""
    trip = _trip({"name": "Nagpur Railway Station", "latitude": 21.1458, "longitude": 79.0882})
    # The geocoder now answers with somewhere else entirely for that name.
    _stub_geocoder(monkeypatch, {
        "Nagpur Railway Station": (0.0, 0.0),
        "Udaipur City Railway Station": UDAIPUR_STATION,
        "Lake City Heritage Hotel, Udaipur": (24.5800, 73.6900),
        "Fateh Sagar Lake, Udaipur": FATEH_SAGAR,
    })

    async def fake_get_route_legs(coordinates):
        return [RouteLeg(i, i + 1, 1.0, 1) for i in range(len(coordinates) - 1)]

    monkeypatch.setattr(route_sequence, "get_route_legs", fake_get_route_legs)

    stops, _, _ = asyncio.run(resolve_sequence(trip))
    assert (stops[0].latitude, stops[0].longitude) == NAGPUR


def test_every_consecutive_pair_gets_a_leg(monkeypatch) -> None:
    """A -> B -> C yields A->B and B->C."""
    trip = _trip(None)
    _stub_geocoder(monkeypatch, {
        "Udaipur City Railway Station": UDAIPUR_STATION,
        "Lake City Heritage Hotel, Udaipur": (24.5800, 73.6900),
        "Fateh Sagar Lake, Udaipur": FATEH_SAGAR,
    })

    async def fake_get_route_legs(coordinates):
        return [RouteLeg(i, i + 1, 2.0, 5) for i in range(len(coordinates) - 1)]

    monkeypatch.setattr(route_sequence, "get_route_legs", fake_get_route_legs)

    stops, legs, _ = asyncio.run(resolve_sequence(trip))

    assert len(legs) == len(stops) - 1
    assert [(leg.from_index, leg.to_index) for leg in legs] == [
        (i, i + 1) for i in range(len(stops) - 1)
    ]


def test_a_routing_outage_yields_null_legs_and_a_reason(monkeypatch) -> None:
    trip = _trip(None)
    _stub_geocoder(monkeypatch, {
        "Udaipur City Railway Station": UDAIPUR_STATION,
        "Lake City Heritage Hotel, Udaipur": (24.5800, 73.6900),
        "Fateh Sagar Lake, Udaipur": FATEH_SAGAR,
    })

    async def failing(coordinates):
        raise RoutingUnavailable("The routing service could not be reached.")

    monkeypatch.setattr(route_sequence, "get_route_legs", failing)

    stops, legs, reason = asyncio.run(resolve_sequence(trip))

    assert reason == "The routing service could not be reached."
    assert len(legs) == len(stops) - 1
    assert all(leg.distance_km is None and leg.duration_minutes is None for leg in legs)
    assert not any(leg.routing_available for leg in legs)


def test_an_unplaceable_stop_leaves_its_legs_unknown(monkeypatch) -> None:
    trip = _trip(None)
    _stub_geocoder(monkeypatch, {
        "Udaipur City Railway Station": UDAIPUR_STATION,
        "Lake City Heritage Hotel, Udaipur": None,  # geocoder knows of no such place
        "Fateh Sagar Lake, Udaipur": FATEH_SAGAR,
    })

    async def fake_get_route_legs(coordinates):
        return [RouteLeg(i, i + 1, 9.9, 30) for i in range(len(coordinates) - 1)]

    monkeypatch.setattr(route_sequence, "get_route_legs", fake_get_route_legs)

    stops, legs, _ = asyncio.run(resolve_sequence(trip))

    hotel = next(stop for stop in stops if stop.label == "Lake City Heritage Hotel")
    assert hotel.resolved is False
    # The legs either side of an unplaced stop are unknown, never zero.
    touching = [leg for leg in legs if hotel.index in (leg.from_index, leg.to_index)]
    assert touching and all(leg.distance_km is None for leg in touching)


def test_no_leg_anywhere_ever_reports_zero_for_unknown(monkeypatch) -> None:
    """The invariant, asserted directly."""
    trip = _trip(None)
    _stub_geocoder(monkeypatch, {})

    stops, legs, reason = asyncio.run(resolve_sequence(trip))

    assert reason is not None
    for leg in legs:
        assert leg.distance_km is None
        assert leg.duration_minutes is None
        assert leg.as_dict()["routing_available"] is False


# --------------------------------------------------------------------------
# Planning request
# --------------------------------------------------------------------------

def test_the_planner_request_accepts_a_boarding_location() -> None:
    request = PlannerRequest(
        destination="Udaipur",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 12),
        budget=30000,
        boarding_location=BoardingLocation(name="Nagpur Railway Station"),
    )
    assert request.boarding_location is not None
    assert request.boarding_location.name == "Nagpur Railway Station"


def test_the_planner_prompt_names_the_starting_point() -> None:
    from app.services.planner_service import _build_prompt

    prompt = _build_prompt(PlannerRequest(
        destination="Udaipur",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 12),
        budget=30000,
        boarding_location=BoardingLocation(name="Nagpur Railway Station"),
    ))

    assert "Nagpur Railway Station" in prompt
    # The model supplies the sequence; OSRM supplies the kilometres.
    assert "Do NOT state distances" in prompt


def test_the_prompt_omits_the_section_when_there_is_no_boarding_location() -> None:
    from app.services.planner_service import _build_prompt

    prompt = _build_prompt(PlannerRequest(
        destination="Udaipur",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 12),
        budget=30000,
    ))
    assert "Journey starts from" not in prompt


# --------------------------------------------------------------------------
# Endpoint behaviour
# --------------------------------------------------------------------------

def _generate_payload(**overrides) -> dict:
    payload = {
        "destination": "Udaipur",
        "start_date": "2026-12-10",
        "end_date": "2026-12-11",
        "budget": 30000,
        "boarding_location": {"name": "Nagpur Railway Station"},
    }
    payload.update(overrides)
    return payload


def test_a_new_trip_without_a_boarding_location_is_refused(
    client: TestClient, user_a_token: str
) -> None:
    response = client.post(
        "/api/trips/generate",
        json=_generate_payload(boarding_location=None),
        headers=auth(user_a_token),
    )
    assert response.status_code == 422
    assert "boarding location is required" in response.json()["detail"].lower()


def test_an_unresolvable_boarding_location_is_refused_by_name(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    """Named in the message, so the user can correct what they typed."""
    async def no_match(query: str):
        return None

    monkeypatch.setattr("app.api.routes.planner.geocode_place", no_match)

    response = client.post(
        "/api/trips/generate",
        json=_generate_payload(boarding_location={"name": "Qqqzzz Nowhere"}),
        headers=auth(user_a_token),
    )
    assert response.status_code == 422
    assert "Qqqzzz Nowhere" in response.json()["detail"]


def test_an_unreachable_geocoder_is_a_retryable_503_not_a_substitution(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    """Never silently fall back to the destination city centre."""
    from app.services.integrations.maps import GeocodingUnavailable

    async def unavailable(query: str):
        raise GeocodingUnavailable("The location service could not be reached.")

    monkeypatch.setattr("app.api.routes.planner.geocode_place", unavailable)

    response = client.post(
        "/api/trips/generate", json=_generate_payload(), headers=auth(user_a_token)
    )
    assert response.status_code == 503


def test_the_route_endpoint_requires_authentication(client: TestClient) -> None:
    unknown = "11111111-1111-1111-1111-111111111111"
    assert client.get(f"/api/trips/{unknown}/route").status_code == 401


def test_another_users_trip_route_is_not_readable(
    client: TestClient, user_a_token: str, user_b_token: str, monkeypatch
) -> None:
    trip = client.post(
        "/api/trips",
        json={
            "title": "Udaipur", "destination": "Udaipur",
            "start_date": "2026-12-10", "end_date": "2026-12-11",
        },
        headers=auth(user_a_token),
    ).json()

    response = client.get(f"/api/trips/{trip['id']}/route", headers=auth(user_b_token))
    assert response.status_code == 404


def test_the_route_endpoint_reports_an_outage_as_200_with_null_legs(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    """The itinerary must still render; it just cannot state travel times."""
    trip = client.post(
        "/api/trips",
        json={
            "title": "Udaipur", "destination": "Udaipur",
            "start_date": "2026-12-10", "end_date": "2026-12-11",
        },
        headers=auth(user_a_token),
    ).json()
    client.post(
        f"/api/trips/{trip['id']}/itinerary",
        json={
            "day_number": 1, "date": "2026-12-10", "title": "Day 1",
            "description": (
                "09:00 | Arrive | Udaipur City Railway Station | 0 | travel\n"
                "11:00 | Hotel | Lake City Heritage Hotel | 4000 | accommodation"
            ),
        },
        headers=auth(user_a_token),
    )

    _stub_geocoder(monkeypatch, {
        "Udaipur City Railway Station": UDAIPUR_STATION,
        "Lake City Heritage Hotel, Udaipur": (24.5800, 73.6900),
    })

    async def failing(coordinates):
        raise RoutingUnavailable("The routing service could not be reached.")

    monkeypatch.setattr(route_sequence, "get_route_legs", failing)

    response = client.get(f"/api/trips/{trip['id']}/route", headers=auth(user_a_token))

    assert response.status_code == 200
    body = response.json()
    assert body["unavailable_reason"]
    assert body["legs"]
    for leg in body["legs"]:
        assert leg["distance_km"] is None
        assert leg["routing_available"] is False


def test_a_trip_with_no_boarding_location_still_returns_a_route(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    """Backward compatibility, end to end."""
    trip = client.post(
        "/api/trips",
        json={
            "title": "Legacy", "destination": "Udaipur",
            "start_date": "2026-12-10", "end_date": "2026-12-11",
        },
        headers=auth(user_a_token),
    ).json()
    assert trip["boarding_location"] is None

    client.post(
        f"/api/trips/{trip['id']}/itinerary",
        json={
            "day_number": 1, "date": "2026-12-10", "title": "Day 1",
            "description": (
                "09:00 | Arrive | Udaipur City Railway Station | 0 | travel\n"
                "11:00 | Hotel | Lake City Heritage Hotel | 4000 | accommodation"
            ),
        },
        headers=auth(user_a_token),
    )

    _stub_geocoder(monkeypatch, {
        "Udaipur City Railway Station": UDAIPUR_STATION,
        "Lake City Heritage Hotel, Udaipur": (24.5800, 73.6900),
    })

    async def fake_get_route_legs(coordinates):
        return [RouteLeg(i, i + 1, 3.8, 14) for i in range(len(coordinates) - 1)]

    monkeypatch.setattr(route_sequence, "get_route_legs", fake_get_route_legs)

    response = client.get(f"/api/trips/{trip['id']}/route", headers=auth(user_a_token))

    assert response.status_code == 200
    body = response.json()
    assert not any(stop["is_boarding"] for stop in body["stops"])
    assert body["stops"][0]["label"] == "Udaipur City Railway Station"
    assert body["legs"][0]["distance_km"] == 3.8


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------

def test_the_boarding_location_survives_a_reload(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    """Refreshing /itinerary/:tripId must still know where the trip starts."""
    from tests.test_planner import fake_generate_trip_plan

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate_trip_plan)

    created = client.post(
        "/api/trips/generate",
        json={
            "destination": "Goa", "start_date": "2026-12-10", "end_date": "2026-12-11",
            "budget": 25000, "boarding_location": {"name": "Nagpur Railway Station"},
        },
        headers=auth(user_a_token),
    )
    assert created.status_code == 201, created.text

    # Fetched fresh, as a page refresh would.
    reloaded = client.get(f"/api/trips/{created.json()['id']}", headers=auth(user_a_token)).json()

    boarding = reloaded["boarding_location"]
    assert boarding is not None
    assert boarding["name"] == "Nagpur Railway Station"
    # Coordinates were resolved server-side and stored, not sent by the browser.
    assert boarding["latitude"] is not None
    assert boarding["longitude"] is not None


def test_the_stored_boarding_location_is_the_geocoded_one_not_the_typed_one(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    from tests.test_planner import fake_generate_trip_plan

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate_trip_plan)

    async def resolves_precisely(query: str):
        return {
            "name": query,
            "display_name": "Nagpur Junction, Nagpur, Maharashtra, 440001, India",
            "latitude": 21.1535,
            "longitude": 79.0882,
        }

    monkeypatch.setattr("app.api.routes.planner.geocode_place", resolves_precisely)

    created = client.post(
        "/api/trips/generate",
        json={
            "destination": "Goa", "start_date": "2026-12-10", "end_date": "2026-12-11",
            "budget": 25000, "boarding_location": {"name": "nagpur station", "latitude": 0, "longitude": 0},
        },
        headers=auth(user_a_token),
    ).json()

    boarding = created["boarding_location"]
    assert boarding["display_name"] == "Nagpur Junction, Nagpur, Maharashtra, 440001, India"
    # Browser-supplied coordinates are ignored in favour of the server's.
    assert boarding["latitude"] == 21.1535


def test_the_boarding_point_is_not_repeated_when_the_plan_opens_there() -> None:
    """Regression, found by generating a real trip.

    The planner opens day one with "Board train from Nagpur Railway Station",
    so the boarding location appeared twice: once as the stop the user chose,
    and again as an itinerary stop qualified into "Nagpur Railway Station,
    Udaipur" — a place that does not exist. That phantom stop never geocoded,
    which killed the legs either side of it and left the real first leg
    reporting as unavailable.
    """
    trip = Trip(destination="Udaipur", boarding_location={
        "name": "Nagpur Railway Station", "latitude": 21.1458, "longitude": 79.0882,
    })
    trip.itinerary_days = [ItineraryDay(
        day_number=1,
        description=(
            "06:00 | Board train | Nagpur Railway Station | 4000 | travel\n"
            "14:00 | Check in | Hotel Lake Palace | 3000 | accommodation"
        ),
    )]

    stops = build_sequence(trip)

    assert [stop.label for stop in stops] == ["Nagpur Railway Station", "Hotel Lake Palace"]
    assert stops[0].is_boarding is True
    # And it is never qualified into a city it is not in.
    assert stops[0].query == "Nagpur Railway Station"


def test_a_boarding_point_mentioned_again_later_is_not_over_collapsed() -> None:
    """Returning to the departure station at the end of a trip is a real leg."""
    trip = Trip(destination="Udaipur", boarding_location={
        "name": "Nagpur Railway Station", "latitude": 21.1458, "longitude": 79.0882,
    })
    trip.itinerary_days = [ItineraryDay(
        day_number=1,
        description=(
            "06:00 | Board | Nagpur Railway Station | 4000 | travel\n"
            "14:00 | Hotel | Hotel Lake Palace | 3000 | accommodation\n"
            "20:00 | Return train | Nagpur Railway Station | 4000 | travel"
        ),
    )]

    labels = [stop.label for stop in build_sequence(trip)]
    assert labels == ["Nagpur Railway Station", "Hotel Lake Palace", "Nagpur Railway Station"]


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        # The planner writes locations for a reader, not for a geocoder.
        ("Hotel Lake Palace, Lake Pichola", "Hotel Lake Palace, Udaipur"),
        ("City Palace, Udaipur", "City Palace, Udaipur"),
        ("Jagdish Temple", "Jagdish Temple, Udaipur"),
        # Already names the city, so it is not doubled up.
        ("Udaipur City Railway Station", "Udaipur City Railway Station"),
    ],
)
def test_a_readable_location_is_reduced_to_a_searchable_one(written: str, expected: str) -> None:
    trip = Trip(destination="Udaipur", boarding_location=None)
    trip.itinerary_days = [ItineraryDay(day_number=1, description=f"09:00 | Stop | {written} | 0 | activity")]

    assert build_sequence(trip)[0].query == expected
    # The label keeps what the planner wrote; only the query is normalised.
    assert build_sequence(trip)[0].label == written


# --------------------------------------------------------------------------
# Trip status is derived from dates, not frozen at creation
# --------------------------------------------------------------------------

def _make_trip(client: TestClient, token: str, start: str, end: str) -> dict:
    return client.post(
        "/api/trips",
        json={"title": "T", "destination": "Udaipur", "start_date": start, "end_date": end},
        headers=auth(token),
    ).json()


def test_a_future_trip_is_upcoming(client: TestClient, user_a_token: str) -> None:
    from datetime import date, timedelta

    start = date.today() + timedelta(days=30)
    trip = _make_trip(client, user_a_token, start.isoformat(), (start + timedelta(days=3)).isoformat())
    assert trip["status"] == "upcoming"


def test_a_trip_under_way_is_still_upcoming(client: TestClient, user_a_token: str) -> None:
    """It has not finished, so it is not in the past."""
    from datetime import date, timedelta

    trip = _make_trip(
        client, user_a_token,
        (date.today() - timedelta(days=1)).isoformat(),
        (date.today() + timedelta(days=2)).isoformat(),
    )
    assert trip["status"] == "upcoming"


def test_a_trip_ending_today_has_not_passed(client: TestClient, user_a_token: str) -> None:
    from datetime import date

    trip = _make_trip(client, user_a_token, date.today().isoformat(), date.today().isoformat())
    assert trip["status"] == "upcoming"


def test_a_finished_trip_reads_as_past(client: TestClient, user_a_token: str) -> None:
    """Regression: the column was written once and never revisited, so the
    dashboard's completed-trip count could only ever be zero."""
    from datetime import date, timedelta

    end = date.today() - timedelta(days=1)
    trip = _make_trip(client, user_a_token, (end - timedelta(days=3)).isoformat(), end.isoformat())
    assert trip["status"] == "past"

    # And on a fresh read, not just on the create response.
    reloaded = client.get(f"/api/trips/{trip['id']}", headers=auth(user_a_token)).json()
    assert reloaded["status"] == "past"


def test_a_deliberate_status_is_not_overwritten(client: TestClient, user_a_token: str) -> None:
    """Date-driven derivation decides upcoming vs past, nothing else."""
    from datetime import date, timedelta

    end = date.today() - timedelta(days=5)
    trip = _make_trip(client, user_a_token, (end - timedelta(days=2)).isoformat(), end.isoformat())
    updated = client.patch(
        f"/api/trips/{trip['id']}", json={"status": "cancelled"}, headers=auth(user_a_token)
    ).json()
    assert updated["status"] == "cancelled"
