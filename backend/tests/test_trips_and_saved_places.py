from datetime import date

from fastapi.testclient import TestClient


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def trip_payload() -> dict[str, object]:
    return {
        "title": "Goa getaway",
        "destination": "Goa",
        "start_date": "2026-12-10",
        "end_date": "2026-12-12",
        "travelers": 2,
        "budget": 25000,
        "preferences": {"interests": ["beaches"]},
        "currency": "INR",
        "status": "planning",
    }


def test_trip_crud_and_user_isolation(client: TestClient, user_a_token: str, user_b_token: str) -> None:
    created = client.post("/api/trips", json=trip_payload(), headers=auth(user_a_token))
    assert created.status_code == 201, created.text
    trip_id = created.json()["id"]

    listed = client.get("/api/trips", headers=auth(user_a_token))
    assert listed.status_code == 200
    assert [trip["id"] for trip in listed.json()] == [trip_id]

    assert client.get(f"/api/trips/{trip_id}", headers=auth(user_b_token)).status_code == 404
    assert client.patch(f"/api/trips/{trip_id}", json={"title": "Hijacked"}, headers=auth(user_b_token)).status_code == 404
    assert client.delete(f"/api/trips/{trip_id}", headers=auth(user_b_token)).status_code == 404

    updated = client.patch(f"/api/trips/{trip_id}", json={"title": "Goa getaway updated"}, headers=auth(user_a_token))
    assert updated.status_code == 200
    assert updated.json()["title"] == "Goa getaway updated"
    assert client.delete(f"/api/trips/{trip_id}", headers=auth(user_a_token)).status_code == 204
    assert client.get(f"/api/trips/{trip_id}", headers=auth(user_a_token)).status_code == 404


def test_saved_place_crud_and_user_isolation(client: TestClient, user_a_token: str, user_b_token: str) -> None:
    payload = {"place_id": "goa-beach", "name": "Candolim Beach", "type": "destination", "category": "Destinations"}
    created = client.post("/api/saved-places", json=payload, headers=auth(user_a_token))
    assert created.status_code == 201, created.text

    listed = client.get("/api/saved-places", headers=auth(user_a_token))
    assert listed.status_code == 200
    assert [place["place_id"] for place in listed.json()] == ["goa-beach"]

    assert client.delete("/api/saved-places/goa-beach", headers=auth(user_b_token)).status_code == 404
    assert client.delete("/api/saved-places/goa-beach", headers=auth(user_a_token)).status_code == 204
    assert client.get("/api/saved-places", headers=auth(user_a_token)).json() == []
