"""Assemble everything an ATLAS e-ticket prints, from stored records only.

This is the seam between the database and the PDF renderer:

    Booking (+ its Trip) -> TicketData -> PDF bytes

Nothing here computes a price, invents a provider, or fabricates a reference.
Every field is either read from a row or left absent so the renderer can omit
the section. That is what keeps a mock booking from reading like a confirmed
reservation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.models.booking import Booking

# The itinerary description format written by the planner route:
# "time | description | location | cost | category". Category was added later,
# so rows created before that have four fields and are still readable.
_ITINERARY_FIELDS = 5

# Cost buckets, in the order the fare summary prints them.
_FARE_CATEGORIES = (
    ("accommodation", "Accommodation"),
    ("travel", "Transportation"),
    ("food", "Food"),
    ("activity", "Activities"),
)


@dataclass
class TicketActivity:
    time: str
    description: str
    location: str
    cost: float
    category: str


@dataclass
class TicketDay:
    day_number: int
    date: date
    title: str
    activities: list[TicketActivity] = field(default_factory=list)


@dataclass
class TicketData:
    """Everything the renderer needs. Optional fields are None when the record
    does not contain them — the renderer omits, never guesses."""

    reference: str
    booking_id: str
    title: str
    booking_type: str
    status: str
    is_mock: bool
    booked_at: datetime
    travel_date: date
    travelers: int
    currency: str
    total_price: float

    lead_traveler_name: str | None = None
    lead_traveler_email: str | None = None
    lead_traveler_phone: str | None = None
    id_document_type: str | None = None

    destination: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    nights: int | None = None
    budget: float | None = None

    days: list[TicketDay] = field(default_factory=list)
    fare_breakdown: list[tuple[str, float]] = field(default_factory=list)
    itinerary_total: float | None = None
    data_sources: list[tuple[str, str]] = field(default_factory=list)
    verify_url: str | None = None

    @property
    def duration_label(self) -> str | None:
        if self.start_date is None or self.end_date is None:
            return None
        days = (self.end_date - self.start_date).days + 1
        nights = max(0, days - 1)
        return f"{days} Day{'s' if days != 1 else ''} / {nights} Night{'s' if nights != 1 else ''}"

    @property
    def remaining_budget(self) -> float | None:
        if self.budget is None or self.itinerary_total is None:
            return None
        return self.budget - self.itinerary_total


def _parse_activities(description: str) -> list[TicketActivity]:
    activities: list[TicketActivity] = []
    for line in (description or "").split("\n"):
        if not line.strip():
            continue
        parts = line.split(" | ")
        if len(parts) < 4:
            continue
        try:
            cost = float(parts[3])
        except (TypeError, ValueError):
            cost = 0.0
        activities.append(
            TicketActivity(
                time=parts[0].strip(),
                description=parts[1].strip(),
                location=parts[2].strip(),
                cost=cost,
                # Rows written before the category field existed are bucketed
                # as activities rather than guessed at from their wording.
                category=parts[4].strip() if len(parts) >= _ITINERARY_FIELDS else "activity",
            )
        )
    return activities


def _fare_breakdown(days: list[TicketDay]) -> tuple[list[tuple[str, float]], float]:
    """Sum the itinerary's own costs per category.

    The totals come from the stored itinerary, not from anything recomputed
    here, so every line traces back to a row the user can see in the app.
    """
    totals = {key: 0.0 for key, _ in _FARE_CATEGORIES}
    for day in days:
        for activity in day.activities:
            if activity.category in totals:
                totals[activity.category] += activity.cost
            else:
                totals["activity"] += activity.cost
    breakdown = [(label, totals[key]) for key, label in _FARE_CATEGORIES]
    return breakdown, sum(totals.values())


def _data_sources(data_context: object) -> list[tuple[str, str]]:
    """Turn the planner's recorded per-agent flags into printable labels.

    Reads the flags the planner actually stored. An agent that is absent from
    the record is not listed at all — silence is honest, a guess is not.
    """
    if not isinstance(data_context, dict):
        return []

    labels = {
        "route": "Route information",
        "weather": "Weather information",
        "hotel": "Accommodation cost",
        "food": "Food information",
        "planner": "Itinerary",
    }
    sources: list[tuple[str, str]] = []
    for key, label in labels.items():
        agent = data_context.get(key)
        if not isinstance(agent, dict) or not isinstance(agent.get("is_realtime_data"), bool):
            continue
        live = agent["is_realtime_data"]
        # The food agent can have live place data while its costs stay an
        # estimate; say both rather than flattening them into one word.
        if key == "food" and live and agent.get("cost_is_estimated"):
            sources.append((label, "Live (OpenStreetMap) — meal costs are AI estimates"))
        elif key == "planner":
            sources.append((label, "AI generated" if live else "AI generated (fallback plan)"))
        elif live:
            sources.append((label, "Live"))
        else:
            sources.append((label, "AI estimate"))
    return sources


def build_ticket(booking: Booking, *, verify_url: str | None = None) -> TicketData:
    """Build the ticket for one booking, pulling trip detail when it is linked."""
    ticket = TicketData(
        reference=booking.reference,
        booking_id=str(booking.id),
        title=booking.title,
        booking_type=booking.booking_type,
        status=booking.status,
        is_mock=bool(booking.is_mock),
        booked_at=booking.created_at,
        travel_date=booking.travel_date,
        travelers=booking.travelers,
        currency=booking.currency,
        total_price=booking.price,
        lead_traveler_name=booking.lead_traveler_name,
        lead_traveler_email=booking.lead_traveler_email,
        lead_traveler_phone=booking.lead_traveler_phone,
        id_document_type=booking.id_document_type,
        verify_url=verify_url,
    )

    trip = booking.trip
    if trip is None:
        return ticket

    ticket.destination = trip.destination
    ticket.start_date = trip.start_date
    ticket.end_date = trip.end_date
    ticket.budget = trip.budget
    ticket.nights = max(0, (trip.end_date - trip.start_date).days)
    ticket.days = [
        TicketDay(
            day_number=day.day_number,
            date=day.date,
            title=day.title,
            activities=_parse_activities(day.description),
        )
        for day in trip.itinerary_days
    ]
    ticket.fare_breakdown, ticket.itinerary_total = _fare_breakdown(ticket.days)
    ticket.data_sources = _data_sources(trip.data_context)
    return ticket
