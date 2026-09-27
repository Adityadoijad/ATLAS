"""Tests for live OpenStreetMap food data (Overpass) and the Food agent.

Every test here is mocked — nothing in this file may touch the real public
Overpass server. The contract under test is that live data is reported as live,
every other outcome falls back honestly, and no OSM value is ever invented.
"""
import asyncio

import httpx
import pytest

from app.schemas.planner import PlannerRequest
from app.services.agents.food import FoodAgent
from app.services.integrations import overpass


def _request(destination: str = "Manali", **overrides) -> PlannerRequest:
    payload = {
        "destination": destination,
        "start_date": "2026-12-10",
        "end_date": "2026-12-12",
        "budget": 25000,
        "travelers": 2,
        "preferences": {},
    }
    payload.update(overrides)
    return PlannerRequest(**payload)


def _node(osm_id: int, name: str | None = "Cafe Example", amenity: str = "restaurant", **tags) -> dict:
    element = {"type": "node", "id": osm_id, "lat": 32.24, "lon": 77.18, "tags": {"amenity": amenity}}
    if name is not None:
        element["tags"]["name"] = name
    element["tags"].update(tags)
    return element


@pytest.fixture(autouse=True)
def _clear_overpass_state():
    """Overpass caching is process-global; isolate every test from the rest."""
    overpass._cache.clear()
    overpass._inflight.clear()
    overpass.food_breaker.failures = 0
    overpass.food_breaker.opened_at = None
    yield
    overpass._cache.clear()
    overpass._inflight.clear()


def _mock_transport(handler):
    """Swap httpx.AsyncClient for one backed by a mock transport."""
    real_client = httpx.AsyncClient

    def factory(*_args, **kwargs):
        kwargs.pop("timeout", None)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    return factory


def _responder(monkeypatch, handler):
    monkeypatch.setattr(overpass.httpx, "AsyncClient", _mock_transport(handler))


def _json_response(elements: list[dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == overpass.OVERPASS_ENDPOINT
        return httpx.Response(200, json={"elements": elements})

    return handler


def _geocodes(monkeypatch, coordinates=None, error: Exception | None = None):
    async def fake_geocode(_destination):
        if error is not None:
            raise error
        return coordinates or {"latitude": 32.24, "longitude": 77.18}

    monkeypatch.setattr("app.services.agents.food.geocode_destination", fake_geocode)


# --------------------------------------------------------------------------
# A. Successful Overpass response
# --------------------------------------------------------------------------

def test_successful_response_is_normalized_and_marked_live(monkeypatch) -> None:
    _responder(monkeypatch, _json_response([
        _node(1, "Johnson's Cafe", "restaurant", cuisine="indian;italian",
              phone="+91 123", website="https://example.com", opening_hours="Mo-Su 09:00-22:00",
              **{"addr:housenumber": "12", "addr:street": "Circuit House Road", "addr:city": "Manali"}),
    ]))
    places = asyncio.run(overpass.get_food_places(32.24, 77.18))

    assert len(places) == 1
    assert places[0] == {
        "name": "Johnson's Cafe",
        "category": "restaurant",
        # OSM's semicolon-separated multi-value tag is split for display.
        "cuisine": "indian, italian",
        "latitude": 32.24,
        "longitude": 77.18,
        "address": "12 Circuit House Road, Manali",
        "phone": "+91 123",
        "website": "https://example.com",
        "opening_hours": "Mo-Su 09:00-22:00",
        "source": "openstreetmap",
        "is_realtime_data": True,
    }


def test_agent_reports_live_places_but_still_flags_cost_as_estimated(monkeypatch) -> None:
    """The central honesty rule: OSM knows where to eat, never what it costs."""
    _geocodes(monkeypatch)
    _responder(monkeypatch, _json_response([_node(1, "Drifters Cafe", "cafe")]))

    result = asyncio.run(FoodAgent().run(_request()))

    assert result["is_realtime_data"] is True
    assert result["cost_is_estimated"] is True
    assert result["source"] == "openstreetmap"
    assert "OpenStreetMap contributors" in str(result["attribution"])
    assert [place["name"] for place in result["places"]] == ["Drifters Cafe"]
    assert "fallback_reason" not in result
    # The recommendation must not imply the budget figure is live data.
    assert "estimated" in str(result["recommendation"]).lower()


# --------------------------------------------------------------------------
# B. Missing OSM tags
# --------------------------------------------------------------------------

def test_missing_tags_become_none_and_are_never_fabricated(monkeypatch) -> None:
    _responder(monkeypatch, _json_response([_node(1, "Bare Bones Dhaba", "restaurant")]))
    [place] = asyncio.run(overpass.get_food_places(32.24, 77.18))

    for field in ("cuisine", "address", "phone", "website", "opening_hours"):
        assert place[field] is None, f"{field} should stay None when OSM has no tag"
    assert place["name"] == "Bare Bones Dhaba"


def test_partial_address_tags_do_not_produce_a_useless_fragment(monkeypatch) -> None:
    """A lone house number is not an address; better to return nothing."""
    _responder(monkeypatch, _json_response([
        _node(1, "Corner Bakery", "bakery", **{"addr:housenumber": "42"}),
    ]))
    [place] = asyncio.run(overpass.get_food_places(32.24, 77.18))
    assert place["address"] is None


def test_unnamed_and_coordinate_less_elements_are_dropped(monkeypatch) -> None:
    _responder(monkeypatch, _json_response([
        _node(1, None, "restaurant"),                                  # no name
        {"type": "way", "id": 2, "tags": {"amenity": "cafe", "name": "No Coords"}},  # no center
        _node(3, "   ", "cafe"),                                       # whitespace-only name
        _node(4, "Real Place", "cafe"),
    ]))
    places = asyncio.run(overpass.get_food_places(32.24, 77.18))
    assert [place["name"] for place in places] == ["Real Place"]


def test_way_and_relation_centers_are_used_for_coordinates(monkeypatch) -> None:
    """Food courts are often mapped as ways/relations, which carry `center`."""
    _responder(monkeypatch, _json_response([
        {"type": "way", "id": 1, "center": {"lat": 32.25, "lon": 77.19},
         "tags": {"amenity": "food_court", "name": "Mall Food Court"}},
    ]))
    [place] = asyncio.run(overpass.get_food_places(32.24, 77.18))
    assert (place["latitude"], place["longitude"]) == (32.25, 77.19)
    assert place["category"] == "food_court"


# --------------------------------------------------------------------------
# C-F. Failure modes all fall back honestly
# --------------------------------------------------------------------------

def test_empty_response_falls_back_with_a_clear_reason(monkeypatch) -> None:
    _geocodes(monkeypatch)
    _responder(monkeypatch, _json_response([]))

    result = asyncio.run(FoodAgent().run(_request()))

    assert result["is_realtime_data"] is False
    assert "no usable restaurant data" in str(result["fallback_reason"])
    assert "places" not in result
    # The estimate itself is still useful and still offered.
    assert "budget for meals" in str(result["recommendation"])


def test_timeout_falls_back(monkeypatch) -> None:
    _geocodes(monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("overpass is slow")

    _responder(monkeypatch, handler)
    result = asyncio.run(FoodAgent().run(_request()))

    assert result["is_realtime_data"] is False
    assert "could not be reached" in str(result["fallback_reason"])


def test_rate_limit_falls_back_without_retrying(monkeypatch) -> None:
    """429 must cost exactly one request — no retry and no failover to another
    instance. Retrying is what the Overpass usage policy forbids, and moving
    the load to a sibling server would just make someone else's day worse."""
    _geocodes(monkeypatch)
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, text="Too Many Requests")

    _responder(monkeypatch, handler)
    result = asyncio.run(FoodAgent().run(_request()))

    assert calls["n"] == 1
    assert result["is_realtime_data"] is False
    assert "rate limited" in str(result["fallback_reason"])


def test_server_error_fails_over_once_to_a_second_instance(monkeypatch) -> None:
    """The main front door periodically 504s while an instance behind it is
    unhealthy, even with rate-limit slots free. One failover covers that; each
    endpoint is still tried at most once."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url) == overpass.OVERPASS_ENDPOINT:
            return httpx.Response(504, text="Gateway Timeout")
        return httpx.Response(200, json={"elements": [_node(1, "Backup Cafe", "cafe")]})

    _responder(monkeypatch, handler)
    places = asyncio.run(overpass.get_food_places(32.24, 77.18))

    assert [place["name"] for place in places] == ["Backup Cafe"]
    assert seen == [overpass.OVERPASS_ENDPOINT, overpass._ENDPOINTS[1]]


def test_every_endpoint_failing_gives_up_rather_than_looping(monkeypatch) -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(504, text="Gateway Timeout")

    _responder(monkeypatch, handler)
    with pytest.raises(overpass.OverpassUnavailable):
        asyncio.run(overpass.get_food_places(32.24, 77.18))
    # One attempt per endpoint, no more.
    assert calls["n"] == len(overpass._ENDPOINTS)


def test_invalid_json_falls_back(monkeypatch) -> None:
    """Overpass reports query errors as an HTML page with HTTP 200."""
    _geocodes(monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>Error: line 1: parse error</body></html>")

    _responder(monkeypatch, handler)
    result = asyncio.run(FoodAgent().run(_request()))
    assert result["is_realtime_data"] is False
    assert "could not be reached" in str(result["fallback_reason"])


def test_http_error_falls_back(monkeypatch) -> None:
    _geocodes(monkeypatch)
    _responder(monkeypatch, lambda _r: httpx.Response(500, text="boom"))
    result = asyncio.run(FoodAgent().run(_request()))
    assert result["is_realtime_data"] is False


def test_ungeocodable_destination_falls_back_without_calling_overpass(monkeypatch) -> None:
    _geocodes(monkeypatch, error=LookupError("Destination was not found"))

    def handler(_request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("Overpass must not be queried without coordinates")

    _responder(monkeypatch, handler)
    result = asyncio.run(FoodAgent().run(_request("Qzxqzxville")))

    assert result["is_realtime_data"] is False
    assert "could not be located" in str(result["fallback_reason"])


# --------------------------------------------------------------------------
# G. Deduplication
# --------------------------------------------------------------------------

def test_duplicate_places_are_collapsed_keeping_the_richer_record(monkeypatch) -> None:
    """OSM often holds both a node and the enclosing building way for one
    venue. They must collapse without losing the tags either one carries."""
    _responder(monkeypatch, _json_response([
        _node(1, "Cafe 1947", "restaurant"),
        {"type": "way", "id": 2, "center": {"lat": 32.2401, "lon": 77.1801},
         "tags": {"amenity": "restaurant", "name": "Cafe 1947",
                  "cuisine": "italian", "phone": "+91 999"}},
    ]))
    places = asyncio.run(overpass.get_food_places(32.24, 77.18))

    assert len(places) == 1
    assert places[0]["cuisine"] == "italian"
    assert places[0]["phone"] == "+91 999"


def test_same_name_far_apart_are_kept_as_separate_branches(monkeypatch) -> None:
    _responder(monkeypatch, _json_response([
        _node(1, "Chai Point", "cafe"),
        {"type": "node", "id": 2, "lat": 32.30, "lon": 77.25,
         "tags": {"amenity": "cafe", "name": "Chai Point"}},
    ]))
    assert len(asyncio.run(overpass.get_food_places(32.24, 77.18))) == 2


# --------------------------------------------------------------------------
# H. Caching and request sharing
# --------------------------------------------------------------------------

def test_repeat_query_within_ttl_makes_no_second_request(monkeypatch) -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"elements": [_node(1, "Cached Cafe", "cafe")]})

    _responder(monkeypatch, handler)
    first = asyncio.run(overpass.get_food_places(32.24, 77.18))
    second = asyncio.run(overpass.get_food_places(32.24, 77.18))

    assert calls["n"] == 1
    assert first == second


def test_expired_cache_entry_refetches(monkeypatch) -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"elements": [_node(1, "Cafe", "cafe")]})

    _responder(monkeypatch, handler)
    asyncio.run(overpass.get_food_places(32.24, 77.18))
    # Age every entry past the TTL.
    for key, (_stamp, value) in list(overpass._cache.items()):
        overpass._cache[key] = (0.0, value)
    asyncio.run(overpass.get_food_places(32.24, 77.18))

    assert calls["n"] == 2


def test_concurrent_callers_for_one_destination_share_a_single_request(monkeypatch) -> None:
    """The planner's food agent and the details page can ask at the same
    moment; that must stay one call against shared public infrastructure."""
    calls = {"n": 0}

    async def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"elements": [_node(1, "Shared Cafe", "cafe")]})

    _responder(monkeypatch, handler)

    async def main():
        return await asyncio.gather(*(overpass.get_food_places(32.24, 77.18) for _ in range(4)))

    results = asyncio.run(main())
    assert calls["n"] == 1
    assert all(result == results[0] for result in results)


def test_different_radius_is_cached_separately(monkeypatch) -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"elements": [_node(1, "Cafe", "cafe")]})

    _responder(monkeypatch, handler)
    asyncio.run(overpass.get_food_places(32.24, 77.18, radius_m=5000))
    asyncio.run(overpass.get_food_places(32.24, 77.18, radius_m=2000))
    assert calls["n"] == 2


# --------------------------------------------------------------------------
# I. Category handling and query construction
# --------------------------------------------------------------------------

@pytest.mark.parametrize("amenity", ["restaurant", "cafe", "fast_food", "food_court", "bakery", "ice_cream"])
def test_each_food_category_is_queried_and_preserved(monkeypatch, amenity: str) -> None:
    _responder(monkeypatch, _json_response([_node(1, f"A {amenity}", amenity)]))
    [place] = asyncio.run(overpass.get_food_places(32.24, 77.18))
    assert place["category"] == amenity
    assert f'"amenity"="{amenity}"' in overpass.build_query(32.24, 77.18, 5000, overpass._FOOD_AMENITIES)


def test_alcohol_venues_are_excluded_unless_requested() -> None:
    default_query = overpass.build_query(32.24, 77.18, 5000, overpass._FOOD_AMENITIES)
    assert '"amenity"="pub"' not in default_query
    assert '"amenity"="bar"' not in default_query

    with_bars = overpass.build_query(32.24, 77.18, 5000, overpass._FOOD_AMENITIES + overpass._BAR_AMENITIES)
    assert '"amenity"="pub"' in with_bars


def test_query_uses_the_requested_radius_and_covers_nodes_ways_relations() -> None:
    query = overpass.build_query(32.24, 77.18, 5000, ("restaurant",))
    assert "(around:5000,32.24,77.18)" in query
    assert query.startswith("[out:json][timeout:")
    assert "nwr[" in query           # nodes, ways and relations
    assert "out center tags;" in query


def test_preferences_rank_matching_cuisines_first_without_dropping_others(monkeypatch) -> None:
    _geocodes(monkeypatch)
    _responder(monkeypatch, _json_response([
        _node(1, "Meat House", "restaurant", cuisine="barbecue"),
        _node(2, "Untagged Place", "restaurant"),
        {"type": "node", "id": 3, "lat": 32.241, "lon": 77.181,
         "tags": {"amenity": "restaurant", "name": "Green Leaf", "cuisine": "vegetarian"}},
    ]))

    result = asyncio.run(FoodAgent().run(_request(preferences={"food": ["Vegetarian"]})))

    names = [place["name"] for place in result["places"]]
    assert names[0] == "Green Leaf"
    # Non-matching places are reordered, never filtered out — OSM's cuisine
    # tag is too sparse to treat its absence as a mismatch.
    assert set(names) == {"Green Leaf", "Meat House", "Untagged Place"}


# --------------------------------------------------------------------------
# J/K. Planner integration and realtime metadata
# --------------------------------------------------------------------------

def test_planner_context_reports_food_live_alongside_other_agents(monkeypatch) -> None:
    """The itinerary banner is built from per-agent metadata, so food going
    live must show up as its own signal, not be hidden by the aggregate."""
    from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema
    from app.services import planner

    async def fake_ai_plan(_request):
        return GeneratedTripPlanSchema(
            title="Manali trip", destination="Manali",
            start_date="2026-12-10", end_date="2026-12-12", total_budget=25000,
            days=[DayPlanSchema(day_number=1, date="2026-12-10", title="Day", activities=[
                ActivitySchema(time="09:00", description="Eat", location="Manali",
                               estimated_cost=500, category="food"),
            ])],
        )

    async def live_agent(*_args):
        return {"is_realtime_data": True}

    _geocodes(monkeypatch)
    monkeypatch.setattr(planner, "generate_ai_trip_plan", fake_ai_plan)
    monkeypatch.setattr(planner.RouteAgent, "run", live_agent)
    monkeypatch.setattr(planner.WeatherAgent, "run", live_agent)
    _responder(monkeypatch, _json_response([_node(1, "Johnson's Cafe", "restaurant")]))

    result = asyncio.run(planner.generate_trip_plan(_request()))
    context = result.data_context

    assert context["food"]["is_realtime_data"] is True
    assert context["food"]["cost_is_estimated"] is True
    assert context["route"]["is_realtime_data"] is True
    assert context["weather"]["is_realtime_data"] is True
    # Hotel is still estimate-only, so the aggregate stays False — and the
    # per-agent detail is what the UI reads.
    assert context["hotel"]["is_realtime_data"] is False
    assert context["is_realtime_data"] is False


def test_planner_still_produces_an_itinerary_when_food_is_degraded(monkeypatch) -> None:
    from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema
    from app.services import planner

    async def fake_ai_plan(_request):
        return GeneratedTripPlanSchema(
            title="Manali trip", destination="Manali",
            start_date="2026-12-10", end_date="2026-12-12", total_budget=25000,
            days=[DayPlanSchema(day_number=1, date="2026-12-10", title="Day", activities=[
                ActivitySchema(time="09:00", description="Eat", location="Manali",
                               estimated_cost=500, category="food"),
            ])],
        )

    _geocodes(monkeypatch)
    monkeypatch.setattr(planner, "generate_ai_trip_plan", fake_ai_plan)
    _responder(monkeypatch, lambda _r: httpx.Response(429, text="Too Many Requests"))

    result = asyncio.run(planner.generate_trip_plan(_request()))

    assert result.plan.days[0].activities[0].category == "food"
    assert result.data_context["food"]["is_realtime_data"] is False
    assert result.data_context["food"]["fallback_reason"]


def test_food_agent_declares_a_longer_timeout_than_the_default() -> None:
    """Overpass is slower than the other integrations; the orchestrator must
    honour a per-agent budget or food would always time out."""
    from app.services.planner import _DEFAULT_AGENT_TIMEOUT

    assert FoodAgent.timeout_seconds > _DEFAULT_AGENT_TIMEOUT
