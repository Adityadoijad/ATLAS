"""Weather pipeline: provider -> integration -> agent -> API.

Every test mocks OpenWeatherMap. The suite must never spend real API quota, so
nothing here performs a live request.

The recurring assertion is not "weather was returned" but "weather was
described accurately" — live data labelled live, absent data labelled absent,
and a date never claimed beyond the five days the free plan actually serves.
"""
import asyncio
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.schemas.planner import PlannerRequest
from app.services.agents.weather import WeatherAgent
from app.services.integrations import weather as weather_module
from app.services.integrations.weather import (
    WeatherUnavailable,
    get_destination_forecast,
    get_trip_weather,
    get_weather,
    get_weather_detailed,
)

# Kolkata's offset, so a UTC evening step lands on the *next* Indian day —
# which is the bug these tests exist to catch.
IST_OFFSET_SECONDS = 5 * 3600 + 1800


@pytest.fixture(autouse=True)
def _reset_weather_state():
    """Caches and breakers are module state; tests must not leak into each other."""
    def clear():
        weather_module._current_cache.clear()
        weather_module._detailed_cache.clear()
        weather_module._forecast_cache.clear()
        for breaker in (weather_module.weather_breaker, weather_module.forecast_breaker):
            breaker.failures = 0
            breaker.opened_at = None

    clear()
    yield
    clear()


@pytest.fixture(autouse=True)
def _no_geocoder(monkeypatch):
    """Default every test to provider name matching, explicitly.

    Without this the geocoder would be exercised incidentally by whatever
    `httpx.AsyncClient.get` happens to be patched to, which makes `located_by`
    an accident of test ordering. Tests about coordinates override it.
    """
    async def unavailable(destination):
        raise LookupError("geocoder not stubbed for this test")

    monkeypatch.setattr(weather_module, "geocode_destination", unavailable)


@pytest.fixture
def configured_key(monkeypatch):
    monkeypatch.setattr(weather_module.settings, "OPENWEATHER_API_KEY", "test-key")
    return "test-key"


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.setattr(weather_module.settings, "OPENWEATHER_API_KEY", "")


# --------------------------------------------------------------------------
# Payload builders
# --------------------------------------------------------------------------

def _current_payload():
    return {
        "name": "Goa",
        "sys": {"country": "IN"},
        "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 70},
        "wind": {"speed": 2.0},
        "weather": [{"description": "clear sky", "icon": "01d"}],
    }


def _forecast_payload(
    *,
    start_utc: datetime | None = None,
    steps: int = 40,
    timezone_offset: int = IST_OFFSET_SECONDS,
    name: str = "Manali",
    country: str = "IN",
):
    """A /forecast response shaped like the real one: 3-hourly steps, UTC `dt`."""
    start = start_utc or datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
    entries = []
    for index in range(steps):
        moment = start + timedelta(hours=3 * index)
        entries.append({
            "dt": int(moment.timestamp()),
            "dt_txt": moment.strftime("%Y-%m-%d %H:%M:%S"),
            "main": {
                "temp": 20.0 + index % 5,
                "temp_min": 18.0 + index % 5,
                "temp_max": 24.0 + index % 5,
                "feels_like": 20.0,
                "humidity": 60,
            },
            "weather": [{"description": "light rain" if index % 2 else "clear sky", "icon": "10d"}],
        })
    return {
        "list": entries,
        "city": {
            "name": name,
            "country": country,
            "coord": {"lat": 32.2396, "lon": 77.1887},
            "timezone": timezone_offset,
        },
    }


def _responder(payload, status: int = 200):
    """Stand in for httpx.AsyncClient.get, capturing the params it was called with."""
    calls: list[dict] = []

    async def fake_get(self, url, params=None):
        calls.append({"url": url, "params": params or {}})
        return httpx.Response(status, json=payload, request=httpx.Request("GET", url))

    return fake_get, calls


# --------------------------------------------------------------------------
# A. Valid key — live data, correctly labelled
# --------------------------------------------------------------------------

def test_forecast_returns_provider_days_and_resolved_destination(monkeypatch, configured_key) -> None:
    fake_get, calls = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(get_destination_forecast("Manali"))

    assert result["resolved_destination"] == "Manali, IN"
    assert result["latitude"] == 32.2396
    assert result["days"], "a successful lookup must carry days"
    # With no geocoder, the destination name is what gets queried.
    assert calls[0]["params"]["q"] == "Manali"
    assert result["located_by"] == "provider_name_match"


def test_every_forecast_day_is_a_real_calendar_day_in_order(monkeypatch, configured_key) -> None:
    fake_get, _ = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    days = asyncio.run(get_destination_forecast("Manali"))["days"]
    dates = [date.fromisoformat(day["date"]) for day in days]

    assert dates == sorted(dates)
    assert len(dates) == len(set(dates)), "one entry per day, no duplicates"
    for day in days:
        assert day["temperature_min_c"] <= day["temperature_max_c"]
        assert day["condition"]


def test_forecast_never_claims_more_days_than_the_provider_sent(monkeypatch, configured_key) -> None:
    # Five days of 3-hourly steps is what the free plan serves.
    fake_get, _ = _responder(_forecast_payload(steps=40))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    days = asyncio.run(get_destination_forecast("Manali"))["days"]
    assert len(days) <= weather_module.FORECAST_HORIZON_DAYS + 1


def test_current_conditions_echo_what_the_provider_geocoded(monkeypatch, configured_key) -> None:
    fake_get, _ = _responder(_current_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(get_weather("Goa"))
    assert result["temperature_c"] == 25.0
    assert result["resolved_destination"] == "Goa, IN"


# --------------------------------------------------------------------------
# Date handling — the destination's calendar, not the server's
# --------------------------------------------------------------------------

def test_days_are_bucketed_by_destination_local_date_not_utc(monkeypatch, configured_key) -> None:
    """A 20:00 UTC step is already the next day in India and must bucket there.

    Grouping on the UTC date would shift an entire evening of readings onto the
    wrong day, so a traveller would read Tuesday's weather under Monday.
    """
    start = datetime(2026, 10, 1, 20, 0, tzinfo=timezone.utc)  # 01:30 on 2 Oct IST
    fake_get, _ = _responder(_forecast_payload(start_utc=start, steps=40))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    days = asyncio.run(get_destination_forecast("Manali"))["days"]
    first = date.fromisoformat(days[0]["date"])

    assert first == date(2026, 10, 2), "20:00 UTC is 01:30 IST the following day"


def test_local_date_follows_the_destination_timezone(monkeypatch, configured_key) -> None:
    fake_get, _ = _responder(_forecast_payload(timezone_offset=IST_OFFSET_SECONDS))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(get_destination_forecast("Manali"))
    expected = (datetime.now(tz=timezone.utc) + timedelta(seconds=IST_OFFSET_SECONDS)).date()
    assert result["local_date"] == expected.isoformat()


def test_a_trip_inside_the_window_gets_its_own_dates(monkeypatch, configured_key) -> None:
    now = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    fake_get, _ = _responder(_forecast_payload(start_utc=now, steps=40))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    local_today = (now + timedelta(seconds=IST_OFFSET_SECONDS)).date()
    start = local_today + timedelta(days=2)
    result = asyncio.run(get_trip_weather("Manali", start, start + timedelta(days=1)))

    assert result["covers_trip_dates"] is True
    assert result["scope"] == "trip_dates"
    returned = {date.fromisoformat(day["date"]) for day in result["days"]}
    assert returned <= {start, start + timedelta(days=1)}
    assert returned, "the trip's own days were available and must be the ones returned"


def test_a_trip_beyond_the_window_is_not_dressed_up_as_a_forecast(monkeypatch, configured_key) -> None:
    """The failure this guards against: showing today's weather as December's."""
    fake_get, _ = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    far = date.today() + timedelta(days=120)
    result = asyncio.run(get_trip_weather("Manali", far, far + timedelta(days=4)))

    assert result["covers_trip_dates"] is False
    assert result["scope"] == "current_outlook"
    # And it says so in words, not only in a flag.
    assert "beyond" in str(result["note"])
    assert far.isoformat() not in [day["date"] for day in result["days"]]


# --------------------------------------------------------------------------
# B/C/D/F. Failure modes
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("status", "fragment"),
    [
        (401, "API key was rejected"),      # B. invalid key
        (404, "does not recognise"),        # F. unknown destination
        (429, "quota is exhausted"),
        (500, "temporarily unavailable"),
    ],
)
def test_provider_errors_become_readable_reasons(monkeypatch, configured_key, status, fragment) -> None:
    fake_get, _ = _responder({"message": "provider text"}, status=status)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(WeatherUnavailable) as raised:
        asyncio.run(get_destination_forecast("Nowhereatall"))
    assert fragment in str(raised.value)


def test_a_rejected_key_is_never_echoed_in_the_failure_message(monkeypatch) -> None:
    """httpx stringifies to the request URL, and the key rides in that URL.

    This is the reason the integration converts provider exceptions instead of
    letting them propagate: the message ends up in logs, in `data_context` and
    in an API response.
    """
    monkeypatch.setattr(weather_module.settings, "OPENWEATHER_API_KEY", "SUPERSECRETKEY")
    fake_get, _ = _responder({"cod": 401, "message": "Invalid API key"}, status=401)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(WeatherUnavailable) as raised:
        asyncio.run(get_destination_forecast("Goa"))

    assert "SUPERSECRETKEY" not in str(raised.value)
    assert "appid" not in str(raised.value)


def test_network_failure_is_reported_without_the_request_url(monkeypatch, configured_key) -> None:
    async def fake_get(self, url, params=None):
        raise httpx.ConnectTimeout("timed out", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(WeatherUnavailable) as raised:
        asyncio.run(get_destination_forecast("Goa"))
    assert "could not be reached" in str(raised.value)
    assert "openweathermap.org" not in str(raised.value)


def test_missing_key_fails_before_any_request_is_made(monkeypatch, no_key) -> None:
    """D. An unconfigured deployment must not call the provider at all."""
    called = False

    async def fake_get(self, url, params=None):
        nonlocal called
        called = True
        return httpx.Response(200, json={}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(WeatherUnavailable) as raised:
        asyncio.run(get_destination_forecast("Goa"))
    assert "not configured" in str(raised.value)
    assert called is False


def test_an_empty_forecast_list_is_a_failure_not_an_empty_success(monkeypatch, configured_key) -> None:
    fake_get, _ = _responder({"list": [], "city": {"name": "Goa", "timezone": 0}})
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(WeatherUnavailable):
        asyncio.run(get_destination_forecast("Goa"))


def test_detailed_lookup_keeps_current_conditions_when_the_forecast_fails(monkeypatch, configured_key) -> None:
    async def fake_get(self, url, params=None):
        if "forecast" in url:
            return httpx.Response(500, json={}, request=httpx.Request("GET", url))
        return httpx.Response(200, json=_current_payload(), request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(get_weather_detailed("Goa"))
    assert result["temperature_c"] == 25.0
    assert result["forecast"] == [], "no forecast is an empty list, never invented days"


# --------------------------------------------------------------------------
# Caching
# --------------------------------------------------------------------------

def test_repeat_lookups_for_one_destination_hit_the_provider_once(monkeypatch, configured_key) -> None:
    fake_get, calls = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    first = asyncio.run(get_destination_forecast("Goa"))
    second = asyncio.run(get_destination_forecast("Goa"))

    assert first == second
    assert len(calls) == 1


def test_one_destination_never_serves_another_destination_weather(monkeypatch, configured_key) -> None:
    """The cache-poisoning failure: Goa's numbers appearing under Manali."""
    async def fake_get(self, url, params=None):
        city = (params or {}).get("q", "")
        payload = _forecast_payload(name=city, country="IN")
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    goa = asyncio.run(get_destination_forecast("Goa"))
    manali = asyncio.run(get_destination_forecast("Manali"))

    assert goa["resolved_destination"] == "Goa, IN"
    assert manali["resolved_destination"] == "Manali, IN"


def test_case_and_whitespace_differences_share_one_cache_entry(monkeypatch, configured_key) -> None:
    fake_get, calls = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    asyncio.run(get_destination_forecast("Goa"))
    asyncio.run(get_destination_forecast("  goa "))
    assert len(calls) == 1


def test_a_failed_lookup_is_not_cached_as_live_weather(monkeypatch, configured_key) -> None:
    """A provider outage must not be replayed as a successful result."""
    state = {"fail": True}

    async def fake_get(self, url, params=None):
        if state["fail"]:
            return httpx.Response(500, json={}, request=httpx.Request("GET", url))
        return httpx.Response(200, json=_forecast_payload(), request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(WeatherUnavailable):
        asyncio.run(get_destination_forecast("Goa"))
    assert weather_module._forecast_cache == {}

    state["fail"] = False
    weather_module.forecast_breaker.failures = 0
    weather_module.forecast_breaker.opened_at = None
    assert asyncio.run(get_destination_forecast("Goa"))["days"]


def test_an_expired_entry_is_refetched(monkeypatch, configured_key) -> None:
    fake_get, calls = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    asyncio.run(get_destination_forecast("Goa"))
    # Age the entry past its TTL.
    stamp, value = weather_module._forecast_cache["goa"]
    weather_module._forecast_cache["goa"] = (stamp - weather_module._CACHE_TTL_SECONDS - 1, value)

    asyncio.run(get_destination_forecast("Goa"))
    assert len(calls) == 2


# --------------------------------------------------------------------------
# Weather agent
# --------------------------------------------------------------------------

def _request(destination: str = "Manali", start: date | None = None, days: int = 2) -> PlannerRequest:
    start = start or date.today() + timedelta(days=1)
    return PlannerRequest(
        destination=destination, start_date=start, end_date=start + timedelta(days=days), budget=1000
    )


def test_agent_queries_the_trip_destination_and_dates(monkeypatch, configured_key) -> None:
    seen = {}

    async def fake_trip_weather(destination, start_date, end_date):
        seen.update(destination=destination, start_date=start_date, end_date=end_date)
        return {"resolved_destination": "Manali, IN", "days": [], "covers_trip_dates": True, "scope": "trip_dates"}

    monkeypatch.setattr("app.services.agents.weather.get_trip_weather", fake_trip_weather)
    request = _request("Manali", date(2026, 12, 10), days=4)

    result = asyncio.run(WeatherAgent().run(request))

    assert seen == {
        "destination": "Manali",
        "start_date": date(2026, 12, 10),
        "end_date": date(2026, 12, 14),
    }
    assert result["is_realtime_data"] is True
    assert result["resolved_destination"] == "Manali, IN"


def test_agent_reports_live_data_that_does_not_reach_the_trip_dates(monkeypatch, configured_key) -> None:
    """Live *and* not about the travel dates is a real combination, so both
    facts are reported rather than one overwriting the other."""
    fake_get, _ = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(WeatherAgent().run(_request(start=date.today() + timedelta(days=200))))

    assert result["is_realtime_data"] is True
    assert result["covers_trip_dates"] is False


def test_agent_falls_back_with_a_meaningful_reason(monkeypatch, configured_key) -> None:
    fake_get, _ = _responder({"message": "quota"}, status=429)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(WeatherAgent().run(_request()))

    assert result["is_realtime_data"] is False
    assert "quota is exhausted" in result["fallback_reason"]
    assert result["forecast"] is None, "fallback carries no weather at all"


def test_agent_fallback_reason_never_contains_the_api_key(monkeypatch) -> None:
    """`fallback_reason` is persisted in data_context and returned to the browser."""
    monkeypatch.setattr(weather_module.settings, "OPENWEATHER_API_KEY", "SUPERSECRETKEY")
    fake_get, _ = _responder({}, status=401)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(WeatherAgent().run(_request()))
    assert "SUPERSECRETKEY" not in result["fallback_reason"]


def test_agent_without_a_configured_key_degrades_rather_than_raising(no_key) -> None:
    result = asyncio.run(WeatherAgent().run(_request()))
    assert result["is_realtime_data"] is False
    assert "not configured" in result["fallback_reason"]


def test_agent_survives_an_unexpected_error(monkeypatch, configured_key) -> None:
    async def explode(destination, start_date, end_date):
        raise ValueError("something structural")

    monkeypatch.setattr("app.services.agents.weather.get_trip_weather", explode)
    result = asyncio.run(WeatherAgent().run(_request()))

    assert result["is_realtime_data"] is False
    assert "ValueError" in result["fallback_reason"]
    # The exception's own text is not forwarded, only its type.
    assert "something structural" not in result["fallback_reason"]


# --------------------------------------------------------------------------
# GET /api/weather/forecast
# --------------------------------------------------------------------------

def test_forecast_endpoint_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/weather/forecast", params={"destination": "Goa"}).status_code == 401


def test_forecast_endpoint_returns_live_days(
    client: TestClient, user_a_token: str, monkeypatch, configured_key
) -> None:
    fake_get, _ = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    response = client.get(
        "/api/weather/forecast",
        params={"destination": "Manali"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_realtime_data"] is True
    assert body["resolved_destination"] == "Manali, IN"
    assert body["days"] and body["unavailable_reason"] is None
    assert body["days"][0]["weekday"]


def test_forecast_endpoint_reports_failure_as_200_with_a_reason(
    client: TestClient, user_a_token: str, monkeypatch, configured_key
) -> None:
    """The dashboard needs to render "unavailable"; a 500 would just break it."""
    fake_get, _ = _responder({}, status=401)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    response = client.get(
        "/api/weather/forecast",
        params={"destination": "Manali"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_realtime_data"] is False
    assert body["days"] == []
    assert "API key was rejected" in body["unavailable_reason"]


def test_forecast_endpoint_never_returns_the_api_key(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    monkeypatch.setattr(weather_module.settings, "OPENWEATHER_API_KEY", "SUPERSECRETKEY")
    fake_get, _ = _responder({}, status=401)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    response = client.get(
        "/api/weather/forecast",
        params={"destination": "Manali"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert "SUPERSECRETKEY" not in response.text


def test_forecast_endpoint_rejects_an_empty_destination(client: TestClient, user_a_token: str) -> None:
    response = client.get(
        "/api/weather/forecast",
        params={"destination": ""},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Locating the destination
# --------------------------------------------------------------------------

def test_the_forecast_is_requested_by_coordinates_not_by_name(monkeypatch, configured_key) -> None:
    """OpenWeatherMap's own name matching puts "Manali" in Chennai.

    Found on a live request: `q=Manali` returned 13.17/80.27 (a Chennai
    neighbourhood) labelled "Manali, IN", while Nominatim — which the route and
    food agents already use — returns 32.24/77.19 in Himachal. Querying by
    coordinate is what keeps every agent talking about the same place.
    """
    fake_get, calls = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    async def fake_geocode(destination):
        return {"latitude": 32.2454608, "longitude": 77.1872926}

    monkeypatch.setattr(weather_module, "geocode_destination", fake_geocode)

    result = asyncio.run(get_destination_forecast("Manali"))

    assert calls[0]["params"]["lat"] == 32.2454608
    assert calls[0]["params"]["lon"] == 77.1872926
    assert "q" not in calls[0]["params"], "a name must not be sent alongside coordinates"
    # The coordinates reported back are the ones actually asked about.
    assert result["latitude"] == 32.2454608
    assert result["located_by"] == "geocoder"


def test_a_geocoder_failure_degrades_to_name_matching_rather_than_no_weather(
    monkeypatch, configured_key
) -> None:
    fake_get, calls = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    async def failing_geocode(destination):
        raise LookupError("Destination was not found")

    monkeypatch.setattr(weather_module, "geocode_destination", failing_geocode)

    result = asyncio.run(get_destination_forecast("Manali"))

    assert calls[0]["params"]["q"] == "Manali"
    assert result["located_by"] == "provider_name_match"
    assert result["days"], "degraded location still returns the provider's weather"


def test_a_name_matched_result_is_cached_only_briefly(monkeypatch, configured_key) -> None:
    """It may be the wrong city, so it must not be served for a full hour."""
    fake_get, calls = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    async def failing_geocode(destination):
        raise LookupError("nope")

    monkeypatch.setattr(weather_module, "geocode_destination", failing_geocode)

    asyncio.run(get_destination_forecast("Manali"))
    stamp, value = weather_module._forecast_cache["manali"]
    # Older than the degraded TTL but well inside the normal one.
    weather_module._forecast_cache["manali"] = (stamp - weather_module._DEGRADED_CACHE_TTL_SECONDS - 1, value)

    asyncio.run(get_destination_forecast("Manali"))
    assert len(calls) == 2, "a name-matched entry expires after the short TTL"


def test_a_geocoded_result_is_cached_for_the_full_hour(monkeypatch, configured_key) -> None:
    fake_get, calls = _responder(_forecast_payload())
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    async def fake_geocode(destination):
        return {"latitude": 32.24, "longitude": 77.18}

    monkeypatch.setattr(weather_module, "geocode_destination", fake_geocode)

    asyncio.run(get_destination_forecast("Manali"))
    stamp, value = weather_module._forecast_cache["manali"]
    weather_module._forecast_cache["manali"] = (stamp - weather_module._DEGRADED_CACHE_TTL_SECONDS - 1, value)

    asyncio.run(get_destination_forecast("Manali"))
    assert len(calls) == 1


def test_two_destinations_are_geocoded_and_queried_separately(monkeypatch, configured_key) -> None:
    coordinates = {"Goa": (15.35, 74.0), "Manali": (32.24, 77.18)}

    async def fake_geocode(destination):
        lat, lon = coordinates[destination]
        return {"latitude": lat, "longitude": lon}

    monkeypatch.setattr(weather_module, "geocode_destination", fake_geocode)

    seen = []

    async def fake_get(self, url, params=None):
        seen.append(((params or {}).get("lat"), (params or {}).get("lon")))
        return httpx.Response(200, json=_forecast_payload(), request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    asyncio.run(get_destination_forecast("Goa"))
    asyncio.run(get_destination_forecast("Manali"))

    assert seen == [(15.35, 74.0), (32.24, 77.18)]


def test_the_agent_declares_a_budget_for_two_round_trips() -> None:
    """Geocode then forecast does not fit the planner's single-call default.

    Regression: with the planner's 2.5s default a cold Goa lookup timed out and
    the trip reported live weather unavailable while OpenWeatherMap was
    answering perfectly well.
    """
    from app.services.planner import _DEFAULT_AGENT_TIMEOUT

    assert WeatherAgent.timeout_seconds > _DEFAULT_AGENT_TIMEOUT
