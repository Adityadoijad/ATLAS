"""Tests for booking records and the e-ticket PDF.

Three things matter here and are tested separately:
  * security    — a ticket is private to its owner
  * integrity   — every printed figure traces back to a stored row
  * honesty     — a mock booking says so, and nothing is invented
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from io import BytesIO

from app.models.booking import Booking


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _booking_payload(**overrides) -> dict:
    payload = {
        "title": "Manali · Personalized Trip Package",
        "booking_type": "Package",
        "travel_date": "2026-12-10",
        "price": 25650,
        "travelers": 2,
        "currency": "INR",
        "lead_traveler_name": "Aditya Doijad",
        "lead_traveler_email": "aditya@example.com",
        "lead_traveler_phone": "9876543210",
    }
    payload.update(overrides)
    return payload


def create_booking(client: TestClient, token: str, **overrides) -> dict:
    response = client.post("/api/bookings", json=_booking_payload(**overrides), headers=auth(token))
    assert response.status_code == 201, response.text
    return response.json()


def ticket_text(client: TestClient, token: str, booking_id: str) -> str:
    response = client.get(f"/api/bookings/{booking_id}/ticket", headers=auth(token))
    assert response.status_code == 200, response.text
    reader = PdfReader(BytesIO(response.content))
    return "".join(page.extract_text() for page in reader.pages)


def _generated_trip(client: TestClient, token: str, monkeypatch) -> dict:
    """Create a real persisted trip through the existing planner endpoint."""
    from app.schemas.planner import ActivitySchema, DayPlanSchema, GeneratedTripPlanSchema
    from app.services.planner import PlannerResult

    async def fake_plan(_request):
        plan = GeneratedTripPlanSchema(
            title="Manali Getaway", destination="Manali",
            start_date=date(2026, 12, 10), end_date=date(2026, 12, 11), total_budget=30000,
            days=[
                DayPlanSchema(day_number=1, date=date(2026, 12, 10), title="Arrival", activities=[
                    ActivitySchema(time="08:00", description="Bus from Delhi", location="Delhi Bus Stand",
                                   estimated_cost=3000, category="travel"),
                    ActivitySchema(time="14:00", description="Check-in at Hotel Snow Valley",
                                   location="Mall Road, Manali", estimated_cost=12000, category="accommodation"),
                    ActivitySchema(time="19:00", description="Himachali thali",
                                   location="Chandni Chowk Restaurant", estimated_cost=850, category="food"),
                ]),
                DayPlanSchema(day_number=2, date=date(2026, 12, 11), title="Exploration", activities=[
                    ActivitySchema(time="10:00", description="Hadimba Temple visit",
                                   location="Hadimba Temple", estimated_cost=400, category="activity"),
                ]),
            ],
        )
        return PlannerResult(plan=plan, data_context={
            "route": {"is_realtime_data": True},
            "weather": {"is_realtime_data": True},
            "hotel": {"is_realtime_data": False, "fallback_reason": "estimated"},
            "food": {"is_realtime_data": True, "cost_is_estimated": True},
            "planner": {"is_realtime_data": True},
            "is_realtime_data": False,
        })

    monkeypatch.setattr("app.api.routes.planner.generate_trip_plan", fake_plan)
    response = client.post(
        "/api/trips/generate",
        json={"destination": "Manali", "start_date": "2026-12-10", "end_date": "2026-12-11", "budget": 30000},
        headers=auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------

def test_ticket_requires_authentication(client: TestClient, user_a_token: str) -> None:
    booking = create_booking(client, user_a_token)
    assert client.get(f"/api/bookings/{booking['id']}/ticket").status_code == 401


def test_owner_can_download_their_own_ticket(client: TestClient, user_a_token: str) -> None:
    booking = create_booking(client, user_a_token)
    response = client.get(f"/api/bookings/{booking['id']}/ticket", headers=auth(user_a_token))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert f"ATLAS-E-Ticket-{booking['reference']}.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")


def test_another_user_cannot_download_someone_elses_ticket(
    client: TestClient, user_a_token: str, user_b_token: str
) -> None:
    """404 rather than 403: confirming the id exists would leak that another
    user holds that booking."""
    booking = create_booking(client, user_a_token)
    response = client.get(f"/api/bookings/{booking['id']}/ticket", headers=auth(user_b_token))
    assert response.status_code == 404


def test_unknown_booking_id_returns_404(client: TestClient, user_a_token: str) -> None:
    unknown = "11111111-1111-1111-1111-111111111111"
    assert client.get(f"/api/bookings/{unknown}/ticket", headers=auth(user_a_token)).status_code == 404


def test_malformed_booking_id_is_rejected(client: TestClient, user_a_token: str) -> None:
    assert client.get("/api/bookings/not-a-uuid/ticket", headers=auth(user_a_token)).status_code == 422


def test_bookings_list_only_returns_your_own(
    client: TestClient, user_a_token: str, user_b_token: str
) -> None:
    create_booking(client, user_a_token, title="Alice trip")
    create_booking(client, user_b_token, title="Bob trip")

    titles = [b["title"] for b in client.get("/api/bookings", headers=auth(user_a_token)).json()]
    assert titles == ["Alice trip"]


def test_cannot_attach_someone_elses_trip_to_a_booking(
    client: TestClient, user_a_token: str, user_b_token: str, monkeypatch
) -> None:
    """Otherwise a ticket could print another user's itinerary."""
    trip = _generated_trip(client, user_a_token, monkeypatch)
    response = client.post(
        "/api/bookings", json=_booking_payload(trip_id=trip["id"]), headers=auth(user_b_token)
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------
# PDF generation
# --------------------------------------------------------------------------

def test_ticket_is_a_non_empty_multi_section_pdf(client: TestClient, user_a_token: str) -> None:
    booking = create_booking(client, user_a_token)
    response = client.get(f"/api/bookings/{booking['id']}/ticket", headers=auth(user_a_token))

    assert len(response.content) > 5000
    reader = PdfReader(BytesIO(response.content))
    assert len(reader.pages) >= 2


def test_ticket_shows_booking_traveller_and_fare_details(client: TestClient, user_a_token: str) -> None:
    booking = create_booking(client, user_a_token)
    text = ticket_text(client, user_a_token, booking["id"])

    assert booking["reference"] in text
    assert "ATLAS" in text and "E-TICKET" in text and "BOOKING CONFIRMATION" in text
    assert "Aditya Doijad" in text
    # The booking total, Indian-formatted, with a rupee sign that actually rendered.
    assert "₹25,650" in text
    assert "Scan to view booking" in text


def test_mock_booking_is_labelled_and_never_claims_payment(client: TestClient, user_a_token: str) -> None:
    booking = create_booking(client, user_a_token)
    text = ticket_text(client, user_a_token, booking["id"])

    assert "DEMO / MOCK BOOKING" in text
    assert "No payment was processed" in text
    assert "no external reservation" in text.lower()
    assert "Not charged (demo)" in text


def test_ticket_invents_no_provider_details(client: TestClient, user_a_token: str, monkeypatch) -> None:
    """The document must never imply a reservation ATLAS does not hold."""
    trip = _generated_trip(client, user_a_token, monkeypatch)
    booking = create_booking(client, user_a_token, trip_id=trip["id"])
    text = ticket_text(client, user_a_token, booking["id"])

    lowered = text.lower()
    for invented in ("pnr:", "flight no", "seat no", "confirmation number", "indigo", "irctc"):
        assert invented not in lowered, f"ticket must not invent {invented!r}"
    assert "AI Estimate / Suggested Accommodation" in text
    assert "Estimated Transportation" in text
    assert "not a confirmed hotel reservation" in text


def test_ticket_reports_the_recorded_data_sources(client: TestClient, user_a_token: str, monkeypatch) -> None:
    """The live/estimate labels must come from the flags the planner stored."""
    trip = _generated_trip(client, user_a_token, monkeypatch)
    booking = create_booking(client, user_a_token, trip_id=trip["id"])
    text = ticket_text(client, user_a_token, booking["id"])

    assert "Data Information" in text
    assert "Route information" in text and "Live" in text
    # Hotel was recorded as an estimate, so it must not read as live.
    assert "Accommodation cost" in text
    assert "AI estimate" in text
    # Food had live places but estimated costs — both facts survive.
    assert "meal costs are AI estimates" in text


def test_ticket_without_a_trip_omits_sections_rather_than_inventing_them(
    client: TestClient, user_a_token: str
) -> None:
    booking = create_booking(client, user_a_token)
    text = ticket_text(client, user_a_token, booking["id"])

    assert "No accommodation is recorded" in text
    assert "No transportation is recorded" in text
    # No trip means no recorded provenance, so the section is absent entirely.
    assert "Data Information" not in text


# --------------------------------------------------------------------------
# Data integrity
# --------------------------------------------------------------------------

def test_reference_is_stable_across_repeated_downloads(client: TestClient, user_a_token: str) -> None:
    """The same booking must always produce the same reference — the ticket,
    the QR code and the user's records have to agree forever."""
    booking = create_booking(client, user_a_token)
    first = ticket_text(client, user_a_token, booking["id"])
    second = ticket_text(client, user_a_token, booking["id"])

    assert booking["reference"] in first
    assert booking["reference"] in second
    listed = client.get("/api/bookings", headers=auth(user_a_token)).json()[0]
    assert listed["reference"] == booking["reference"]


def test_references_are_unique_across_bookings(client: TestClient, user_a_token: str) -> None:
    references = {create_booking(client, user_a_token)["reference"] for _ in range(5)}
    assert len(references) == 5
    assert all(ref.startswith("ATL-") for ref in references)


def test_fare_categories_match_the_stored_itinerary(
    client: TestClient, user_a_token: str, db_session, monkeypatch
) -> None:
    """Every printed amount must trace back to a row, and the categories must
    sum to the itinerary estimate."""
    trip = _generated_trip(client, user_a_token, monkeypatch)
    booking = create_booking(client, user_a_token, trip_id=trip["id"], price=25650)
    text = ticket_text(client, user_a_token, booking["id"])

    # 3000 travel + 12000 accommodation + 850 food + 400 activity = 16250
    assert "₹12,000" in text   # Accommodation
    assert "₹3,000" in text    # Transportation
    assert "₹850" in text      # Food
    assert "₹400" in text      # Activities
    assert "₹16,250" in text   # Itinerary estimate
    # The booking total is the booking's own figure, not a recomputation.
    assert "₹25,650" in text


def test_budget_line_uses_the_stored_trip_budget(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    trip = _generated_trip(client, user_a_token, monkeypatch)
    booking = create_booking(client, user_a_token, trip_id=trip["id"])
    text = ticket_text(client, user_a_token, booking["id"])

    assert "₹30,000" in text   # budget
    assert "Remaining ₹13,750" in text  # 30000 - 16250


def test_destination_and_dates_come_from_the_linked_trip(
    client: TestClient, user_a_token: str, monkeypatch
) -> None:
    trip = _generated_trip(client, user_a_token, monkeypatch)
    booking = create_booking(client, user_a_token, trip_id=trip["id"])
    text = ticket_text(client, user_a_token, booking["id"])

    assert "Manali" in text
    assert "10 Dec 2026" in text and "11 Dec 2026" in text
    assert "Hadimba Temple visit" in text


def test_traveller_count_is_reported_without_inventing_names(
    client: TestClient, user_a_token: str
) -> None:
    booking = create_booking(client, user_a_token, travelers=3)
    text = ticket_text(client, user_a_token, booking["id"])

    assert "3 Travellers" in text
    # Only the lead traveller is known; the rest must not be given names.
    assert "Not provided" in text


def test_price_accepts_a_currency_formatted_string(client: TestClient, user_a_token: str) -> None:
    """Reuses the planner's normalizer so a formatted amount is not rejected."""
    booking = create_booking(client, user_a_token, price="₹25,650")
    assert booking["price"] == 25650.0


def test_cancelling_a_booking_is_reflected_on_the_ticket(client: TestClient, user_a_token: str) -> None:
    booking = create_booking(client, user_a_token)
    cancel = client.post(f"/api/bookings/{booking['id']}/cancel", headers=auth(user_a_token))
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    assert "CANCELLED" in ticket_text(client, user_a_token, booking["id"])


def test_qr_payload_is_a_public_reference_not_a_secret(
    client: TestClient, user_a_token: str, db_session
) -> None:
    """QR codes are readable by anyone holding the ticket, so the payload must
    carry no token or personal data."""
    from app.services.ticket_data import build_ticket

    booking_row = db_session.query(Booking).first() or None
    created = create_booking(client, user_a_token)
    booking_row = db_session.query(Booking).filter(Booking.reference == created["reference"]).one()

    ticket = build_ticket(booking_row, verify_url=f"http://localhost:5173/bookings/{booking_row.reference}")
    assert ticket.verify_url is not None
    assert booking_row.reference in ticket.verify_url
    assert "token" not in ticket.verify_url.lower()
    assert (booking_row.lead_traveler_email or "") not in ticket.verify_url


@pytest.mark.parametrize("amount, expected", [(0, "₹0"), (1500, "₹1,500"), (2534000, "₹25,34,000")])
def test_amounts_use_indian_digit_grouping(amount: int, expected: str) -> None:
    from app.services.ticket_pdf import _money

    assert _money(amount, "INR", unicode_ok=True) == expected


def test_money_falls_back_to_ascii_without_the_unicode_font() -> None:
    """Better a readable 'Rs.' than a missing-glyph box."""
    from app.services.ticket_pdf import _money

    assert _money(1500, "INR", unicode_ok=False) == "Rs. 1,500"
