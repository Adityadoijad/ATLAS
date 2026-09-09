from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.rate_limit import ai_rate_limiter
from app.main import app
from app.models.base import Base
from app.models import ItineraryDay, SavedPlace, Trip, User  # noqa: F401 - registers model metadata


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(test_engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    ai_rate_limiter.reset()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    ai_rate_limiter.reset()


def register_and_login(client: TestClient, *, email: str, name: str = "Atlas Tester") -> str:
    response = client.post("/api/auth/register", json={"email": email, "name": name, "password": "correct-horse-battery"})
    assert response.status_code == 201, response.text
    response = client.post("/api/auth/login", data={"username": email, "password": "correct-horse-battery"})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def user_a_token(client: TestClient) -> str:
    return register_and_login(client, email="alice@atlasapp.dev", name="Alice")


@pytest.fixture
def user_b_token(client: TestClient) -> str:
    return register_and_login(client, email="bob@atlasapp.dev", name="Bob")
