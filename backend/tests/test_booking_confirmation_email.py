"""Tests for emailing a booking confirmation.

The property that matters most: a booking is a database fact and email is a
best-effort side channel. No email outcome may ever disturb the booking.
"""
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.services import email_service
from app.services.email_service import EmailDeliveryError, EmailNotConfiguredError


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_booking(client: TestClient, token: str, **overrides) -> dict:
    payload = {
        "title": "Manali · Personalized Trip Package",
        "booking_type": "Package",
        "travel_date": "2026-12-10",
        "price": 28500,
        "travelers": 2,
        "lead_traveler_name": "Aditya Doijad",
    }
    payload.update(overrides)
    response = client.post("/api/bookings", json=payload, headers=auth(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def sent(monkeypatch):
    """Capture outbound mail at the SMTP boundary, so everything above it —
    recipient selection, PDF generation, MIME assembly — is really exercised."""
    calls: list[dict] = []

    async def fake_send(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.services.booking_email.send_email", fake_send)
    return calls


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_service.settings, "SMTP_FROM_EMAIL", "no-reply@atlas.test")


@pytest.fixture
def unconfigured(monkeypatch):
    """Force the no-mail-server case.

    Without this the test depends on the developer's own .env: it passed while
    SMTP was unset and broke the moment real credentials were added.
    """
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "")
    monkeypatch.setattr(email_service.settings, "SMTP_FROM_EMAIL", "")


# --------------------------------------------------------------------------
# Successful delivery
# --------------------------------------------------------------------------

def test_sends_to_the_authenticated_accounts_own_address(client: TestClient, user_a_token: str, sent) -> None:
    """The recipient comes from the database, never from the request."""
    booking = create_booking(client, user_a_token)
    response = client.post(f"/api/bookings/{booking['id']}/confirmation-email", headers=auth(user_a_token))

    assert response.status_code == 200, response.text
    assert len(sent) == 1, "the email service must be called exactly once"
    assert sent[0]["to_address"] == "alice@atlasapp.dev"
    # The response masks the address rather than echoing it in full.
    assert response.json()["recipient"] == "al***@atlasapp.dev"
    assert response.json()["status"] == "sent"


def test_attaches_the_same_pdf_the_user_can_download(
    client: TestClient, user_a_token: str, sent
) -> None:
    """The attachment must be the existing e-ticket, not a second document."""
    booking = create_booking(client, user_a_token)
    client.post(f"/api/bookings/{booking['id']}/confirmation-email", headers=auth(user_a_token))

    downloaded = client.get(f"/api/bookings/{booking['id']}/ticket", headers=auth(user_a_token)).content
    attachment = sent[0]["attachment"]

    assert attachment.mime_type == "application/pdf"
    assert attachment.content.startswith(b"%PDF-")
    # Byte-for-byte equality is not expected: the PDF embeds a generation
    # timestamp. Equality of *content* is what matters.
    emailed_text = "".join(p.extract_text() for p in PdfReader(BytesIO(attachment.content)).pages)
    downloaded_text = "".join(p.extract_text() for p in PdfReader(BytesIO(downloaded)).pages)
    assert emailed_text.split("Generated on")[0] == downloaded_text.split("Generated on")[0]
    assert booking["reference"] in emailed_text


def test_attachment_filename_follows_the_agreed_pattern(client: TestClient, user_a_token: str, sent) -> None:
    booking = create_booking(client, user_a_token)
    response = client.post(f"/api/bookings/{booking['id']}/confirmation-email", headers=auth(user_a_token))

    expected = f"ATLAS_Booking_Confirmation_{booking['reference']}.pdf"
    assert sent[0]["attachment"].filename == expected
    assert response.json()["attachment_filename"] == expected


def test_subject_and_body_carry_the_booking_details(client: TestClient, user_a_token: str, sent) -> None:
    booking = create_booking(client, user_a_token)
    client.post(f"/api/bookings/{booking['id']}/confirmation-email", headers=auth(user_a_token))

    call = sent[0]
    assert call["subject"] == f"ATLAS Booking Confirmation — {booking['reference']}"
    for body in (call["text_body"], call["html_body"]):
        assert "ATLAS" in body
        assert booking["reference"] in body
        assert "Aditya" in body
        assert "attached" in body.lower()
    # A demo booking must say so in the email as well as on the ticket.
    assert "no payment" in call["text_body"].lower()


def test_body_does_not_leak_contact_details_beyond_the_recipient(
    client: TestClient, user_a_token: str, sent
) -> None:
    booking = create_booking(
        client, user_a_token, lead_traveler_phone="9876543210", lead_traveler_email="other@example.com"
    )
    client.post(f"/api/bookings/{booking['id']}/confirmation-email", headers=auth(user_a_token))

    for body in (sent[0]["text_body"], sent[0]["html_body"]):
        assert "9876543210" not in body
        assert "other@example.com" not in body


# --------------------------------------------------------------------------
# Failure must never touch the booking
# --------------------------------------------------------------------------

def _booking_is_intact(client: TestClient, token: str, booking: dict) -> None:
    listed = client.get("/api/bookings", headers=auth(token)).json()
    assert [b["id"] for b in listed] == [booking["id"]]
    assert listed[0]["reference"] == booking["reference"]
    assert listed[0]["status"] == "upcoming"
    # …and the PDF is still downloadable, which is the user's fallback.
    assert client.get(f"/api/bookings/{booking['id']}/ticket", headers=auth(token)).status_code == 200


def test_delivery_failure_returns_502_and_leaves_the_booking_confirmed(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    async def boom(**_kwargs):
        raise EmailDeliveryError("The mail server could not be reached.")

    monkeypatch.setattr("app.services.booking_email.send_email", boom)
    booking = create_booking(client, user_a_token)
    response = client.post(f"/api/bookings/{booking['id']}/confirmation-email", headers=auth(user_a_token))

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "still confirmed" in detail
    assert "download" in detail.lower()
    _booking_is_intact(client, user_a_token, booking)


def test_missing_configuration_returns_503_and_leaves_the_booking_confirmed(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    async def not_configured(**_kwargs):
        raise EmailNotConfiguredError("Outbound email is not configured on this server.")

    monkeypatch.setattr("app.services.booking_email.send_email", not_configured)
    booking = create_booking(client, user_a_token)
    response = client.post(f"/api/bookings/{booking['id']}/confirmation-email", headers=auth(user_a_token))

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
    _booking_is_intact(client, user_a_token, booking)


def test_creating_a_booking_never_sends_email_by_itself(
    client: TestClient, user_a_token: str, sent
) -> None:
    """Email is opt-in and separate, so a mail outage can never cost a booking."""
    create_booking(client, user_a_token)
    assert sent == []


# --------------------------------------------------------------------------
# Authorization
# --------------------------------------------------------------------------

def test_unauthenticated_request_is_rejected(client: TestClient, user_a_token: str, sent) -> None:
    booking = create_booking(client, user_a_token)
    assert client.post(f"/api/bookings/{booking['id']}/confirmation-email").status_code == 401
    assert sent == []


def test_cannot_email_another_users_booking(
    client: TestClient, user_a_token: str, user_b_token: str, sent
) -> None:
    """Otherwise one user could push another user's itinerary into their inbox."""
    booking = create_booking(client, user_a_token)
    response = client.post(f"/api/bookings/{booking['id']}/confirmation-email", headers=auth(user_b_token))

    assert response.status_code == 404
    assert sent == [], "no mail may be sent for a booking the caller does not own"


def test_unknown_booking_returns_404(client: TestClient, user_a_token: str, sent) -> None:
    unknown = "11111111-1111-1111-1111-111111111111"
    assert client.post(f"/api/bookings/{unknown}/confirmation-email", headers=auth(user_a_token)).status_code == 404
    assert sent == []


def test_each_user_gets_their_own_address(
    client: TestClient, user_a_token: str, user_b_token: str, sent
) -> None:
    """Guards against a hardcoded or cached recipient."""
    a = create_booking(client, user_a_token)
    b = create_booking(client, user_b_token)
    client.post(f"/api/bookings/{a['id']}/confirmation-email", headers=auth(user_a_token))
    client.post(f"/api/bookings/{b['id']}/confirmation-email", headers=auth(user_b_token))

    assert [call["to_address"] for call in sent] == ["alice@atlasapp.dev", "bob@atlasapp.dev"]


# --------------------------------------------------------------------------
# Capability reporting
# --------------------------------------------------------------------------

def test_capability_is_false_without_smtp_configuration(
    client: TestClient, user_a_token: str, unconfigured
) -> None:
    response = client.get("/api/bookings/email-capability", headers=auth(user_a_token))
    assert response.status_code == 200
    assert response.json() == {"available": False}


def test_capability_is_true_once_configured(client: TestClient, user_a_token: str, configured) -> None:
    assert client.get("/api/bookings/email-capability", headers=auth(user_a_token)).json() == {"available": True}


def test_capability_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/bookings/email-capability").status_code == 401


# --------------------------------------------------------------------------
# The SMTP layer itself
# --------------------------------------------------------------------------

def test_send_email_refuses_when_unconfigured(unconfigured) -> None:
    import asyncio

    with pytest.raises(EmailNotConfiguredError):
        asyncio.run(email_service.send_email(
            to_address="someone@example.com", subject="s", text_body="t", html_body="<p>t</p>"))


def test_message_is_multipart_with_a_pdf_attachment(configured) -> None:
    message = email_service._build_message(
        to_address="traveller@example.com",
        subject="ATLAS Booking Confirmation — ATL-ABC123",
        text_body="plain",
        html_body="<p>rich</p>",
        attachment=email_service.Attachment(filename="ticket.pdf", content=b"%PDF-1.4 fake", mime_type="application/pdf"),
    )

    assert message["To"] == "traveller@example.com"
    assert "no-reply@atlas.test" in message["From"]
    attachments = [p for p in message.iter_attachments()]
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_filename() == "ticket.pdf"
    assert attachments[0].get_payload(decode=True) == b"%PDF-1.4 fake"
    # A text alternative survives for clients that block HTML.
    assert "plain" in message.get_body(preferencelist=("plain",)).get_content()


def test_smtp_failures_are_mapped_to_a_delivery_error(configured, monkeypatch) -> None:
    import asyncio
    import smtplib

    def explode(_message):
        raise smtplib.SMTPServerDisconnected("connection lost")

    monkeypatch.setattr(email_service, "_send_blocking", explode)
    with pytest.raises(EmailDeliveryError):
        asyncio.run(email_service.send_email(
            to_address="someone@example.com", subject="s", text_body="t", html_body="<p>t</p>"))


def test_authentication_failure_does_not_surface_the_credential(configured, monkeypatch, caplog) -> None:
    """A rejected password must never end up in the logs."""
    import asyncio
    import smtplib

    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "super-secret-app-password")

    def explode(_message):
        raise smtplib.SMTPAuthenticationError(535, b"Bad credentials")

    monkeypatch.setattr(email_service, "_send_blocking", explode)
    with caplog.at_level("DEBUG"), pytest.raises(EmailDeliveryError):
        asyncio.run(email_service.send_email(
            to_address="someone@example.com", subject="s", text_body="t", html_body="<p>t</p>"))

    assert "super-secret-app-password" not in caplog.text


def test_recipient_is_masked_in_logs(configured, monkeypatch, caplog) -> None:
    import asyncio

    monkeypatch.setattr(email_service, "_send_blocking", lambda _message: None)
    with caplog.at_level("INFO"):
        asyncio.run(email_service.send_email(
            to_address="aditya.doijad@example.com", subject="s", text_body="t", html_body="<p>t</p>"))

    assert "aditya.doijad@example.com" not in caplog.text
    assert "ad" in caplog.text and "@example.com" in caplog.text


@pytest.mark.parametrize(
    "address, expected",
    [
        ("aditya@example.com", "ad****@example.com"),
        # A short local part reveals only its first character — showing two of
        # two would be no masking at all.
        ("ab@example.com", "a**@example.com"),
        ("a@example.com", "a**@example.com"),
        ("not-an-email", "***"),
    ],
)
def test_mask_email(address: str, expected: str) -> None:
    assert email_service.mask_email(address) == expected
