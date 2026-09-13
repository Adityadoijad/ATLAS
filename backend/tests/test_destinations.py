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
