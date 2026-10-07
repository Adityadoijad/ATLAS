from fastapi.testclient import TestClient


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_destination_details_requires_auth(client: TestClient) -> None:
    response = client.get("/api/destinations/Goa/details")
    assert response.status_code == 401


def test_destination_details_full_success(client: TestClient, user_a_token: str, monkeypatch) -> None:
    async def fake_geocode(_destination):
        return {"latitude": 15.3, "longitude": 74.0}

    async def fake_weather(_destination):
        return {
            "temperature_c": 28.5, "feels_like_c": 30.1, "humidity_percent": 70,
            "wind_speed_ms": 3.2, "condition": "clear sky", "icon": "01d", "forecast": [],
        }

    async def fake_activities(_lat, _lon, _limit=8):
        return [{"name": "Fort Aguada", "category": "Historic", "rating": 4.5, "address": None, "latitude": 15.3, "longitude": 74.0, "source": "OpenTripMap"}]

    async def fake_restaurants(_lat, _lon, _limit=8):
        return [{"name": "Britto's", "category": "Seafood", "rating": 4.6, "address": "Baga Beach", "latitude": 15.3, "longitude": 74.0, "source": "Foursquare"}]

    monkeypatch.setattr("app.services.destination_details_service.geocode_destination", fake_geocode)
    monkeypatch.setattr("app.services.destination_details_service.get_weather_detailed", fake_weather)
    monkeypatch.setattr("app.services.destination_details_service.get_activities", fake_activities)
    monkeypatch.setattr("app.services.destination_details_service.get_restaurants", fake_restaurants)

    response = client.get("/api/destinations/Goa/details", headers=auth(user_a_token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_realtime_location"] is True
    assert body["weather"]["is_realtime_data"] is True
    assert body["weather"]["temperature_c"] == 28.5
    assert len(body["activities"]) == 1
    assert body["activities"][0]["name"] == "Fort Aguada"
    assert body["activities_unavailable_reason"] is None
    assert len(body["restaurants"]) == 1
    assert body["restaurants_unavailable_reason"] is None


def test_destination_details_weather_failure_does_not_block_others(client: TestClient, user_a_token: str, monkeypatch) -> None:
    async def fake_geocode(_destination):
        return {"latitude": 15.3, "longitude": 74.0}

    async def failing_weather(_destination):
        raise RuntimeError("OpenWeatherMap is not configured")

    async def fake_activities(_lat, _lon, _limit=8):
        return [{"name": "Fort Aguada", "category": "Historic", "rating": 4.5, "address": None, "latitude": 15.3, "longitude": 74.0, "source": "OpenTripMap"}]

    async def fake_restaurants(_lat, _lon, _limit=8):
        return []

    monkeypatch.setattr("app.services.destination_details_service.geocode_destination", fake_geocode)
    monkeypatch.setattr("app.services.destination_details_service.get_weather_detailed", failing_weather)
    monkeypatch.setattr("app.services.destination_details_service.get_activities", fake_activities)
    monkeypatch.setattr("app.services.destination_details_service.get_restaurants", fake_restaurants)

    response = client.get("/api/destinations/Goa/details", headers=auth(user_a_token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["weather"]["is_realtime_data"] is False
    assert body["weather"]["unavailable_reason"] is not None
    assert len(body["activities"]) == 1  # unaffected by weather failure
    assert body["restaurants"] == []
    assert body["restaurants_unavailable_reason"] == "No results found nearby."


def test_destination_details_geocode_failure_marks_places_unavailable(client: TestClient, user_a_token: str, monkeypatch) -> None:
    async def failing_geocode(_destination):
        raise LookupError("Destination was not found")

    async def fake_weather(_destination):
        return {
            "temperature_c": 28.5, "feels_like_c": 30.1, "humidity_percent": 70,
            "wind_speed_ms": 3.2, "condition": "clear sky", "icon": "01d", "forecast": [],
        }

    monkeypatch.setattr("app.services.destination_details_service.geocode_destination", failing_geocode)
    monkeypatch.setattr("app.services.destination_details_service.get_weather_detailed", fake_weather)

    response = client.get("/api/destinations/Nowhereville/details", headers=auth(user_a_token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_realtime_location"] is False
    assert body["latitude"] is None
    assert body["activities"] == []
    assert body["activities_unavailable_reason"] == "Location could not be determined."
    assert body["restaurants_unavailable_reason"] == "Location could not be determined."
    # Weather doesn't depend on geocoding (OpenWeather geocodes by name itself).
    assert body["weather"]["is_realtime_data"] is True


def test_destination_details_unconfigured_places_api_surfaces_reason(client: TestClient, user_a_token: str, monkeypatch) -> None:
    async def fake_geocode(_destination):
        return {"latitude": 15.3, "longitude": 74.0}

    async def fake_weather(_destination):
        return {
            "temperature_c": 28.5, "feels_like_c": 30.1, "humidity_percent": 70,
            "wind_speed_ms": 3.2, "condition": "clear sky", "icon": "01d", "forecast": [],
        }

    async def unconfigured_activities(_lat, _lon, _limit=8):
        raise RuntimeError("OpenTripMap is not configured")

    async def unconfigured_restaurants(_lat, _lon, _limit=8):
        raise RuntimeError("Foursquare is not configured")

    monkeypatch.setattr("app.services.destination_details_service.geocode_destination", fake_geocode)
    monkeypatch.setattr("app.services.destination_details_service.get_weather_detailed", fake_weather)
    monkeypatch.setattr("app.services.destination_details_service.get_activities", unconfigured_activities)
    monkeypatch.setattr("app.services.destination_details_service.get_restaurants", unconfigured_restaurants)

    response = client.get("/api/destinations/Goa/details", headers=auth(user_a_token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["activities"] == []
    assert body["activities_unavailable_reason"] == "Data currently unavailable"
    assert body["restaurants"] == []
    assert body["restaurants_unavailable_reason"] == "Data currently unavailable"


# --------------------------------------------------------------------------
# Destination photo
# --------------------------------------------------------------------------

def test_photo_endpoint_returns_a_real_photo(client, monkeypatch) -> None:
    async def fake_photo(name: str, state: str):
        return {
            "url": f"https://commons.example/{name}.jpg",
            "source": "Wikimedia Commons",
            "source_url": "https://commons.example/File",
            "author": "Someone",
            "license": "CC BY-SA 4.0",
        }

    monkeypatch.setattr("app.api.routes.destinations.get_destination_photo_with_metadata", fake_photo)

    body = client.get("/api/destinations/Manali/photo").json()
    assert body["destination"] == "Manali"
    assert body["url"] == "https://commons.example/Manali.jpg"
    assert body["license"] == "CC BY-SA 4.0"


def test_photo_endpoint_reports_absence_rather_than_another_place(client, monkeypatch) -> None:
    """The bug this replaced: every unknown destination fell back to a Goa
    beach photo, so a Manali trip rendered Goa under a Manali heading."""
    async def no_photo(name: str, state: str):
        return {"url": None, "source": None, "source_url": None, "author": None, "license": None}

    monkeypatch.setattr("app.api.routes.destinations.get_destination_photo_with_metadata", no_photo)

    body = client.get("/api/destinations/Nowhereatall/photo").json()
    assert body["url"] is None
    assert "goa" not in str(body).lower()


def test_each_destination_is_queried_for_its_own_photo(client, monkeypatch) -> None:
    queried: list[str] = []

    async def record(name: str, state: str):
        queried.append(name)
        return {"url": f"https://x/{name}.jpg", "source": None, "source_url": None, "author": None, "license": None}

    monkeypatch.setattr("app.api.routes.destinations.get_destination_photo_with_metadata", record)

    goa = client.get("/api/destinations/Goa/photo").json()["url"]
    manali = client.get("/api/destinations/Manali/photo").json()["url"]

    assert queried == ["Goa", "Manali"]
    assert goa != manali, "a destination must never inherit another's photograph"


def test_opentripmap_popularity_is_not_presented_as_a_star_rating(monkeypatch) -> None:
    """`rate` is a 1-7 importance tier, not a rating out of five.

    Passing it through rendered "1.0" beside a star icon on real landmarks —
    Nehru Park and a Buddhist monastery both looked one-star.
    """
    import asyncio

    import httpx

    from app.services.integrations import places as places_module

    async def fake_get(self, url, params=None):
        payload = [{
            "name": "Nehru Park",
            "rate": 1,
            "kinds": "natural,parks",
            "point": {"lat": 32.2396, "lon": 77.1887},
        }]
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(places_module.settings, "OPENTRIPMAP_API_KEY", "test-key")
    places_module.activities_breaker.failures = 0
    places_module.activities_breaker.opened_at = None

    results = asyncio.run(places_module.get_activities(32.2396, 77.1887, 5))

    assert results, "the attraction itself is still returned"
    assert results[0]["name"] == "Nehru Park"
    assert results[0]["rating"] is None
