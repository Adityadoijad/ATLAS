from fastapi.testclient import TestClient


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_recommendations_requires_auth(client: TestClient) -> None:
    response = client.get("/api/recommendations")
    assert response.status_code == 401


def test_recommendations_fallback_for_new_user(client: TestClient, user_a_token: str) -> None:
    response = client.get("/api/recommendations", headers=auth(user_a_token))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 6
    assert all(item["reason"] == "Popular with ATLAS travellers" for item in body)
    assert all(item["score"] == 0.0 for item in body)
    # Fallback ranks by rating; several destinations tie at the top rating
    # (4.9) and ties are shuffled per-request for variety, so just confirm
    # the top pick is one of the actual top-rated destinations.
    assert body[0]["destination_id"] in {"mumbai", "kyoto", "swiss-alps"}


def test_recommendations_reflect_saved_place_categories(client: TestClient, user_a_token: str) -> None:
    headers = auth(user_a_token)
    response = client.post(
        "/api/saved-places",
        json={"place_id": "calangute", "name": "Calangute Beach", "type": "beach", "category": "beaches"},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    response = client.get("/api/recommendations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    top = body[0]
    assert top["score"] > 0
    assert top["destination_id"] in {"kerala", "goa", "bali", "santorini"}  # all tagged "beaches"
    assert "Beaches" in top["reason"]


def test_recommendations_reflect_trip_preferences(client: TestClient, user_a_token: str, monkeypatch) -> None:
    from app.services.planner import PlannerResult
    from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema

    async def fake_generate_trip_plan(request):
        return PlannerResult(
            plan=GeneratedTripPlanSchema(
                title="Kolkata", destination="Kolkata", start_date=request.start_date, end_date=request.end_date,
                total_budget=request.budget,
                days=[DayPlanSchema(day_number=1, date=request.start_date, title="Arrival", activities=[
                    ActivitySchema(time="10:00", description="Explore", location="Kolkata", estimated_cost=500)
                ])],
            ),
            data_context={"is_realtime_data": False},
        )

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_generate_trip_plan)

    headers = auth(user_a_token)
    response = client.post(
        "/api/trips/generate",
        json={
            "destination": "Kolkata",
            "start_date": "2026-12-10",
            "end_date": "2026-12-11",
            "budget": 10000,
            "preferences": {"interests": ["culture", "food"]},
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    response = client.get("/api/recommendations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    top = body[0]
    assert top["score"] > 0
    assert top["destination_id"] in {"kolkata", "mumbai", "goa", "kyoto"}  # tagged both culture and food


def test_recommendations_reflect_saved_destination_by_id(client: TestClient, user_a_token: str) -> None:
    """Saving a destination card (e.g. the heart button) persists place_id="goa"
    with a generic category="Destinations" — this must still count as a real
    signal by resolving "goa" against the known destination catalog."""
    headers = auth(user_a_token)
    response = client.post(
        "/api/saved-places",
        json={"place_id": "goa", "name": "Goa", "type": "destination", "category": "Destinations"},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    response = client.get("/api/recommendations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    top = body[0]
    assert top["score"] > 0
    assert top["destination_id"] in {"goa", "kerala", "mumbai", "kolkata"}  # share a tag with goa


def test_recommendations_are_isolated_per_user(client: TestClient, user_a_token: str, user_b_token: str) -> None:
    client.post(
        "/api/saved-places",
        json={"place_id": "kolkata-heritage", "name": "Victoria Memorial", "type": "landmark", "category": "culture"},
        headers=auth(user_a_token),
    )

    response_a = client.get("/api/recommendations", headers=auth(user_a_token))
    response_b = client.get("/api/recommendations", headers=auth(user_b_token))

    assert response_a.json()[0]["score"] > 0
    assert response_b.json()[0]["score"] == 0.0
    assert response_b.json()[0]["reason"] == "Popular with ATLAS travellers"
