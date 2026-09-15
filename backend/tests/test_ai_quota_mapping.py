from fastapi.testclient import TestClient

from app.services.ai_service import AIConfigurationError, AIQuotaExceededError


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_trip_generate_maps_provider_quota_exhaustion_to_structured_429(client: TestClient, user_a_token: str, monkeypatch) -> None:
    """An upstream 429 from the AI provider must surface as ATLAS's own
    structured 429 (with Retry-After), never a generic 502 and never a
    silently fabricated fallback itinerary."""
    async def quota_exhausted(*args, **kwargs):
        raise AIQuotaExceededError("The AI provider's rate limit is exhausted right now.")

    monkeypatch.setattr("app.services.planner_service.generate", quota_exhausted)

    response = client.post(
        "/api/trips/generate",
        json={
            "destination": "Goa",
            "start_date": "2026-12-10",
            "end_date": "2026-12-11",
            "budget": 10000,
        },
        headers=auth(user_a_token),
    )

    assert response.status_code == 429, response.text
    assert response.headers.get("Retry-After") is not None
    assert "quota" in response.json()["detail"].lower()


def test_chat_maps_provider_quota_exhaustion_to_structured_429(client: TestClient, monkeypatch) -> None:
    async def quota_exhausted(*args, **kwargs):
        raise AIQuotaExceededError("quota exhausted")

    monkeypatch.setattr("app.services.chat_service.generate", quota_exhausted)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 429, response.text
    assert response.headers.get("Retry-After") is not None
    assert "quota" in response.json()["detail"].lower()


def test_chat_maps_missing_api_key_to_503(client: TestClient, monkeypatch) -> None:
    async def not_configured(*args, **kwargs):
        raise AIConfigurationError("GROQ_API_KEY is not set.")

    monkeypatch.setattr("app.services.chat_service.generate", not_configured)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 503, response.text
    assert "not configured" in response.json()["detail"].lower()


def test_trip_generate_maps_missing_api_key_to_503(client: TestClient, user_a_token: str, monkeypatch) -> None:
    async def not_configured(*args, **kwargs):
        raise AIConfigurationError("GROQ_API_KEY is not set.")

    monkeypatch.setattr("app.services.planner_service.generate", not_configured)

    response = client.post(
        "/api/trips/generate",
        json={
            "destination": "Goa",
            "start_date": "2026-12-10",
            "end_date": "2026-12-11",
            "budget": 10000,
        },
        headers=auth(user_a_token),
    )

    assert response.status_code == 503, response.text
