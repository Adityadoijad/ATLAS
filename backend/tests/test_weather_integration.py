import httpx
import pytest

from app.services.integrations import weather as weather_module
from app.services.integrations.weather import get_weather, get_weather_detailed


@pytest.fixture(autouse=True)
def _clear_weather_cache():
    weather_module._current_cache.clear()
    weather_module._detailed_cache.clear()
    yield
    weather_module._current_cache.clear()
    weather_module._detailed_cache.clear()


def _current_payload():
    return {
        "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 70},
        "wind": {"speed": 2.0},
        "weather": [{"description": "clear sky", "icon": "01d"}],
    }


def test_get_weather_caches_repeat_calls_for_same_destination_and_day(monkeypatch) -> None:
    call_count = 0

    async def fake_get(self, url, params=None):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=_current_payload(), request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(weather_module.settings, "OPENWEATHER_API_KEY", "test-key")

    import asyncio
    result_1 = asyncio.run(get_weather("Goa"))
    result_2 = asyncio.run(get_weather("Goa"))

    assert result_1 == result_2
    assert call_count == 1  # second call served from cache, no second HTTP request


def test_get_weather_detailed_429_maps_to_exception_not_raw_crash(monkeypatch) -> None:
    async def fake_get(self, url, params=None):
        request = httpx.Request("GET", url)
        return httpx.Response(429, json={"message": "quota exceeded"}, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(weather_module.settings, "OPENWEATHER_API_KEY", "test-key")

    import asyncio
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(get_weather_detailed("Goa"))


def test_weather_agent_treats_429_as_fallback_not_crash(monkeypatch) -> None:
    from datetime import date
    from app.schemas.planner import PlannerRequest
    from app.services.agents.weather import WeatherAgent

    async def failing_get_weather(_destination):
        raise httpx.HTTPStatusError("429", request=httpx.Request("GET", "http://x"), response=httpx.Response(429, request=httpx.Request("GET", "http://x")))

    monkeypatch.setattr("app.services.agents.weather.get_weather", failing_get_weather)

    import asyncio
    request = PlannerRequest(destination="Goa", start_date=date(2026, 12, 10), end_date=date(2026, 12, 10), budget=1000)
    result = asyncio.run(WeatherAgent().run(request))

    assert result["is_realtime_data"] is False
    assert "fallback_reason" in result
