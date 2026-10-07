"""Tests for the persisted Lost & Found board.

The board is intentionally public to signed-in travellers, so "isolation" here
means ownership cannot be forged or borrowed — not that reports are hidden.
"""
import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.lost_found import LostFoundReport
from app.services import lost_found_media

# A real 1x1 JPEG and PNG, so signature checking is exercised for what it is.
JPEG_BYTES = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
    "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="
)
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides) -> dict:
    payload = {
        "title": "Black DSLR camera bag",
        "report_type": "lost",
        "category": "Electronics",
        "location": "Baga Beach, Goa",
        "reported_date": "2026-08-02",
        "description": "Left near the shack seating around sunset.",
        "contact": "In-app message",
    }
    payload.update(overrides)
    return payload


def data_url(payload: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{base64.b64encode(payload).decode()}"


@pytest.fixture(autouse=True)
def _isolated_uploads(tmp_path, monkeypatch):
    """Never write test photos into the real uploads directory."""
    target = tmp_path / "lost-found"
    monkeypatch.setattr(lost_found_media, "LOST_FOUND_DIR", target)
    yield target


def create(client: TestClient, token: str, **overrides):
    return client.post("/api/lost-found", json=_payload(**overrides), headers=auth(token))


# --------------------------------------------------------------------------
# Create and persist
# --------------------------------------------------------------------------

def test_report_is_created_and_persists(client: TestClient, user_a_token: str) -> None:
    response = create(client, user_a_token)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Black DSLR camera bag"
    assert body["status"] == "Open"
    assert body["is_mine"] is True

    # Survives a fresh request — the point of persisting at all.
    listed = client.get("/api/lost-found", headers=auth(user_a_token)).json()
    assert [item["id"] for item in listed] == [body["id"]]


def test_report_is_stored_against_the_authenticated_user(
    client: TestClient, user_a_token: str, db_session
) -> None:
    """Ownership comes from the session, so it cannot be forged."""
    response = create(client, user_a_token)
    row = db_session.query(LostFoundReport).one()
    assert str(row.id) == response.json()["id"]
    assert row.user_id is not None


def test_client_supplied_owner_is_ignored(
    client: TestClient, user_a_token: str, user_b_token: str, db_session
) -> None:
    other = client.get("/api/auth/me", headers=auth(user_b_token)).json()
    response = client.post(
        "/api/lost-found",
        json={**_payload(), "user_id": other["id"]},
        headers=auth(user_a_token),
    )
    assert response.status_code == 201
    mine = db_session.query(LostFoundReport).one()
    assert str(mine.user_id) != other["id"], "user_id must never come from the request body"


def test_board_is_shared_but_ownership_is_marked(
    client: TestClient, user_a_token: str, user_b_token: str
) -> None:
    """Other travellers' reports are visible — that is the product — but only
    the caller's own rows are flagged as theirs."""
    create(client, user_a_token, title="Alice lost a bag")
    create(client, user_b_token, title="Bob found a wallet", report_type="found")

    seen = client.get("/api/lost-found", headers=auth(user_a_token)).json()
    by_title = {item["title"]: item for item in seen}
    assert set(by_title) == {"Alice lost a bag", "Bob found a wallet"}
    assert by_title["Alice lost a bag"]["is_mine"] is True
    assert by_title["Bob found a wallet"]["is_mine"] is False


def test_response_does_not_expose_the_reporter(client: TestClient, user_a_token: str) -> None:
    body = create(client, user_a_token).json()
    assert "user_id" not in body
    assert "alice@atlasapp.dev" not in str(body)
    # Only the contact *preference* the reporter chose to publish.
    assert body["contact"] == "In-app message"


def test_newest_reports_come_first(client: TestClient, user_a_token: str) -> None:
    create(client, user_a_token, title="Older")
    create(client, user_a_token, title="Newer")
    titles = [item["title"] for item in client.get("/api/lost-found", headers=auth(user_a_token)).json()]
    assert titles == ["Newer", "Older"]


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------

def test_listing_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/lost-found").status_code == 401


def test_creating_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/lost-found", json=_payload()).status_code == 401


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"report_type": "misplaced"},          # outside the allowed literal
        {"reported_date": "not-a-date"},
        {"location": ""},
        {"description": ""},
    ],
)
def test_invalid_reports_are_rejected(client: TestClient, user_a_token: str, overrides: dict) -> None:
    assert create(client, user_a_token, **overrides).status_code == 422


def test_nothing_is_written_when_validation_fails(
    client: TestClient, user_a_token: str, db_session
) -> None:
    create(client, user_a_token, title="")
    assert db_session.query(LostFoundReport).count() == 0


# --------------------------------------------------------------------------
# Photos live on disk, not in the database
# --------------------------------------------------------------------------

def test_photo_is_written_to_disk_and_only_its_path_is_stored(
    client: TestClient, user_a_token: str, db_session, _isolated_uploads: Path
) -> None:
    response = create(client, user_a_token, image_data_url=data_url(JPEG_BYTES))
    assert response.status_code == 201

    stored = db_session.query(LostFoundReport).one()
    assert stored.image_url.startswith("/uploads/lost-found/")
    # The row holds a reference; the bytes are on disk.
    assert "base64" not in (stored.image_url or "")
    written = list(_isolated_uploads.glob("*.jpg"))
    assert len(written) == 1
    assert written[0].read_bytes() == JPEG_BYTES


def test_png_is_accepted_and_named_by_its_real_signature(
    client: TestClient, user_a_token: str, _isolated_uploads: Path
) -> None:
    create(client, user_a_token, image_data_url=data_url(PNG_BYTES, "image/png"))
    assert len(list(_isolated_uploads.glob("*.png"))) == 1


def test_a_declared_type_that_contradicts_the_bytes_is_rejected(
    client: TestClient, user_a_token: str, db_session
) -> None:
    """A payload claiming to be an image but carrying something else must not
    be written, whatever its mime type says."""
    hostile = base64.b64encode(b"<?php echo 1; ?>").decode()
    response = create(client, user_a_token, image_data_url=f"data:image/jpeg;base64,{hostile}")
    assert response.status_code == 422
    assert db_session.query(LostFoundReport).count() == 0


@pytest.mark.parametrize(
    "value",
    ["not-a-data-url", "data:text/html;base64,PGgxPmhpPC9oMT4=", "data:image/jpeg;base64,!!!not-base64!!!"],
)
def test_malformed_image_payloads_are_rejected(client: TestClient, user_a_token: str, value: str) -> None:
    assert create(client, user_a_token, image_data_url=value).status_code == 422


def test_oversized_images_are_refused(client: TestClient, user_a_token: str, monkeypatch) -> None:
    monkeypatch.setattr(lost_found_media, "MAX_IMAGE_BYTES", 64)
    payload = JPEG_BYTES + b"\x00" * 200
    assert create(client, user_a_token, image_data_url=data_url(payload)).status_code == 422


def test_report_without_a_photo_stores_no_path(client: TestClient, user_a_token: str) -> None:
    assert create(client, user_a_token).json()["image_url"] is None


# --------------------------------------------------------------------------
# Owner-only deletion
# --------------------------------------------------------------------------

def test_owner_can_withdraw_their_report(
    client: TestClient, user_a_token: str, db_session, _isolated_uploads: Path
) -> None:
    created = create(client, user_a_token, image_data_url=data_url(JPEG_BYTES)).json()
    assert client.delete(f"/api/lost-found/{created['id']}", headers=auth(user_a_token)).status_code == 204

    assert db_session.query(LostFoundReport).count() == 0
    # The photo goes with it rather than lingering on disk.
    assert list(_isolated_uploads.glob("*.jpg")) == []


def test_another_user_cannot_delete_your_report(
    client: TestClient, user_a_token: str, user_b_token: str, db_session
) -> None:
    created = create(client, user_a_token).json()
    response = client.delete(f"/api/lost-found/{created['id']}", headers=auth(user_b_token))

    # 404, not 403: confirming the id exists would leak who filed it.
    assert response.status_code == 404
    assert db_session.query(LostFoundReport).count() == 1


def test_deleting_an_unknown_report_returns_404(client: TestClient, user_a_token: str) -> None:
    unknown = "11111111-1111-1111-1111-111111111111"
    assert client.delete(f"/api/lost-found/{unknown}", headers=auth(user_a_token)).status_code == 404


def test_deleting_requires_authentication(client: TestClient, user_a_token: str) -> None:
    created = create(client, user_a_token).json()
    assert client.delete(f"/api/lost-found/{created['id']}").status_code == 401


# --------------------------------------------------------------------------
# Media helper internals
# --------------------------------------------------------------------------

def test_delete_ignores_paths_outside_the_uploads_directory(_isolated_uploads: Path, tmp_path: Path) -> None:
    """A stored path must never be able to reach beyond uploads."""
    outsider = tmp_path / "keep-me.txt"
    outsider.write_text("important")

    lost_found_media.delete_stored_image("/uploads/lost-found/../../keep-me.txt")
    lost_found_media.delete_stored_image("/etc/passwd")
    lost_found_media.delete_stored_image(None)

    assert outsider.exists()
