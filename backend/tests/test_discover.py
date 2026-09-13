from fastapi.testclient import TestClient


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_discover_requires_auth(client: TestClient) -> None:
    response = client.post("/api/recommendations/discover")
    assert response.status_code == 401


def test_discover_returns_generated_suggestions(client: TestClient, user_a_token: str, monkeypatch) -> None:
    from app.schemas.recommendations import DiscoveredDestinationSchema

    async def fake_generate(_user):
        return [
            DiscoveredDestinationSchema(
                name="Hoi An", country="Vietnam", description="Lantern-lit ancient town.",
                categories=["Culture", "Food"], estimated_budget_inr=55000, best_season="Feb – Apr",
                duration_days=5,
            )
        ]

    monkeypatch.setattr("app.api.routes.recommendations.generate_discoveries", fake_generate)

    response = client.post("/api/recommendations/discover", headers=auth(user_a_token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Hoi An"
    assert body[0]["estimated_budget_inr"] == 55000.0


def test_discover_currency_formatted_budget_is_normalized(client: TestClient, user_a_token: str, monkeypatch) -> None:
    async def fake_generate(_user):
        from app.schemas.recommendations import DiscoveredDestinationSchema
        return [DiscoveredDestinationSchema.model_validate({
            "name": "Hoi An", "country": "Vietnam", "description": "Lantern-lit ancient town.",
            "categories": ["Culture", "Food"], "estimated_budget_inr": "₹55,000", "best_season": "Feb – Apr",
            "duration_days": 5,
        })]

    monkeypatch.setattr("app.api.routes.recommendations.generate_discoveries", fake_generate)

    response = client.post("/api/recommendations/discover", headers=auth(user_a_token))
    assert response.status_code == 200, response.text
    assert response.json()[0]["estimated_budget_inr"] == 55000.0


def test_discover_maps_generation_failure_to_502(client: TestClient, user_a_token: str, monkeypatch) -> None:
    from app.services.discover_service import DiscoveryGenerationError

    async def failing_generate(_user):
        raise DiscoveryGenerationError("AI returned suggestions that didn't match the required format.")

    monkeypatch.setattr("app.api.routes.recommendations.generate_discoveries", failing_generate)

    response = client.post("/api/recommendations/discover", headers=auth(user_a_token))
    assert response.status_code == 502


def test_discover_maps_configuration_error_to_503(client: TestClient, user_a_token: str, monkeypatch) -> None:
    from app.services.discover_service import DiscoveryConfigurationError

    async def failing_generate(_user):
        raise DiscoveryConfigurationError("GEMINI_API_KEY is not set.")

    monkeypatch.setattr("app.api.routes.recommendations.generate_discoveries", failing_generate)

    response = client.post("/api/recommendations/discover", headers=auth(user_a_token))
    assert response.status_code == 503


def test_discover_rejects_invalid_category_free_text(client: TestClient, user_a_token: str, monkeypatch) -> None:
    """A destination-shaped payload with a budget that isn't a real number at
    all (no digits) must fail validation, not silently coerce to 0."""
    from pydantic import ValidationError
    from app.schemas.recommendations import DiscoveredDestinationSchema

    try:
        DiscoveredDestinationSchema.model_validate({
            "name": "Hoi An", "country": "Vietnam", "description": "Lantern-lit ancient town.",
            "categories": ["Culture"], "estimated_budget_inr": "cheap", "best_season": "Feb – Apr",
            "duration_days": 5,
        })
        assert False, "expected a ValidationError"
    except ValidationError:
        pass


def test_discover_rate_limited_after_five_requests(client: TestClient, user_a_token: str, monkeypatch) -> None:
    from app.schemas.recommendations import DiscoveredDestinationSchema

    async def fake_generate(_user):
        return [DiscoveredDestinationSchema(
            name="Hoi An", country="Vietnam", description="Lantern-lit ancient town.",
            categories=["Culture"], estimated_budget_inr=55000, best_season="Feb – Apr", duration_days=5,
        )]

    monkeypatch.setattr("app.api.routes.recommendations.generate_discoveries", fake_generate)

    headers = auth(user_a_token)
    for _ in range(5):
        assert client.post("/api/recommendations/discover", headers=headers).status_code == 200
    assert client.post("/api/recommendations/discover", headers=headers).status_code == 429
