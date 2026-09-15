from fastapi.testclient import TestClient
from google.api_core.exceptions import ResourceExhausted


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_trip_generate_maps_gemini_quota_exhaustion_to_structured_429(client: TestClient, user_a_token: str, monkeypatch) -> None:
    import google.generativeai as genai

    def quota_exhausted(self, prompt):
        raise ResourceExhausted("429 quota exceeded")

    # Patch at the actual Gemini SDK call boundary (not planner_service's
    # wrapper) so the real ResourceExhausted -> PlannerQuotaExceededError
    # conversion in _generate_plan_sync actually runs.
    monkeypatch.setattr(genai.GenerativeModel, "generate_content", quota_exhausted)

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


def test_chat_maps_gemini_quota_exhaustion_to_structured_429(client: TestClient, monkeypatch) -> None:
    async def quota_exhausted(_message):
        from app.services.gemini_service import GeminiQuotaExceededError
        raise GeminiQuotaExceededError("quota exhausted")

    monkeypatch.setattr("app.api.routes.chat.gemini_chat", quota_exhausted)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 429, response.text
    assert response.headers.get("Retry-After") is not None
    assert "quota" in response.json()["detail"].lower()
