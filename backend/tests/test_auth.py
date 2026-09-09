from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from tests.conftest import register_and_login


def test_registration_login_and_current_user(client: TestClient) -> None:
    token = register_and_login(client, email="traveler@atlasapp.dev", name="Traveler")
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "traveler@atlasapp.dev"


def test_registration_rejects_duplicate_email(client: TestClient) -> None:
    register_and_login(client, email="duplicate@atlasapp.dev")
    response = client.post("/api/auth/register", json={"email": "duplicate@atlasapp.dev", "name": "Duplicate", "password": "correct-horse-battery"})
    assert response.status_code == 400


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    register_and_login(client, email="credentials@atlasapp.dev")
    response = client.post("/api/auth/login", data={"username": "credentials@atlasapp.dev", "password": "wrong-password"})
    assert response.status_code == 400


def test_current_user_rejects_missing_and_expired_tokens(client: TestClient, user_a_token: str) -> None:
    assert client.get("/api/auth/me").status_code == 401

    expired = create_access_token("not-a-user", expires_delta=timedelta(seconds=-1))
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
