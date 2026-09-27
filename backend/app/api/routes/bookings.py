"""Booking records and their e-tickets.

Bookings are simulations — nothing here contacts a provider or takes payment.
What it does provide is a durable, owned record, which is what makes a
re-downloadable e-ticket with a stable reference possible at all.
"""
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.booking import Booking
from app.models.trip import Trip
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingEmailResponse, BookingResponse, EmailCapability
from app.services.booking_email import send_booking_confirmation
from app.services.email_service import (
    EmailDeliveryError,
    EmailNotConfiguredError,
    is_configured as email_is_configured,
    mask_email,
)
from app.services.ticket_data import build_ticket
from app.services.ticket_pdf import generate_ticket_pdf

router = APIRouter(prefix="/bookings", tags=["bookings"])

_REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alike characters


def _generate_reference(db: Session) -> str:
    """A human-readable reference, assigned once and then immutable.

    Retries on the (vanishingly unlikely) collision rather than trusting luck,
    because the column is unique and the insert would otherwise fail.
    """
    for _ in range(10):
        candidate = "ATL-" + "".join(secrets.choice(_REFERENCE_ALPHABET) for _ in range(6))
        if not db.query(Booking).filter(Booking.reference == candidate).first():
            return candidate
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not allocate a booking reference. Please try again.",
    )


def _verify_url(booking: Booking) -> str:
    """Public, non-sensitive verification target printed into the QR code."""
    return f"{settings.FRONTEND_URL.rstrip('/')}/bookings/{booking.reference}"


def _owned_booking(booking_id: UUID, db: Session, user: User) -> Booking:
    """Fetch a booking the caller owns.

    A booking belonging to someone else returns 404, not 403: confirming that
    an id exists would leak that another user has that booking.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == user.id).first()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


@router.get("/email-capability", response_model=EmailCapability)
def email_capability(_: User = Depends(get_current_user)) -> EmailCapability:
    """Whether this deployment can send email at all.

    The UI asks first so it can hide the action on a server with no mail
    configured, instead of offering a button that is guaranteed to fail.
    """
    return EmailCapability(available=email_is_configured())


@router.get("", response_model=list[BookingResponse])
def list_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    """Record a booking simulation. No payment is taken and no provider is contacted."""
    trip_id = None
    if payload.trip_id is not None:
        # Only link a trip the caller owns — otherwise the e-ticket would print
        # someone else's itinerary.
        trip = db.query(Trip).filter(Trip.id == payload.trip_id, Trip.user_id == current_user.id).first()
        if trip is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
        trip_id = trip.id

    booking = Booking(
        user_id=current_user.id,
        trip_id=trip_id,
        reference=_generate_reference(db),
        title=payload.title,
        booking_type=payload.booking_type,
        travel_date=payload.travel_date,
        price=payload.price,
        currency=payload.currency.upper(),
        travelers=payload.travelers,
        status="upcoming",
        lead_traveler_name=payload.lead_traveler_name,
        lead_traveler_email=payload.lead_traveler_email,
        lead_traveler_phone=payload.lead_traveler_phone,
        id_document_type=payload.id_document_type,
        is_mock=True,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    booking = _owned_booking(booking_id, db, current_user)
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/{booking_id}/ticket")
def download_ticket(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """The booking's e-ticket as a PDF.

    Private to the owner. The PDF is rendered from the stored booking and its
    linked trip, so the same booking always produces the same reference, the
    same fare and the same QR payload.
    """
    booking = _owned_booking(booking_id, db, current_user)

    # A public, non-sensitive verification target. Never a token or any
    # personal detail — QR codes are readable by anyone who sees the ticket.
    pdf = generate_ticket_pdf(build_ticket(booking, verify_url=_verify_url(booking)))

    filename = f"ATLAS-E-Ticket-{booking.reference}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # The browser fetches this with an Authorization header, so the
            # filename has to survive a blob download too — the frontend reads
            # it back from here rather than inventing its own.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/{booking_id}/confirmation-email", response_model=BookingEmailResponse)
async def email_confirmation(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingEmailResponse:
    """Email the booking's e-ticket to the owner's registered address.

    Deliberately separate from booking creation. A booking is a database fact;
    email is a best-effort side channel that depends on a third party. Coupling
    them would mean a mail outage could cost somebody a confirmed booking.

    This endpoint therefore only ever reads. Whatever happens to the message,
    the booking is untouched and the PDF stays downloadable.

    The recipient is the owning account's address, read from the database —
    never supplied by the caller.
    """
    booking = _owned_booking(booking_id, db, current_user)
    recipient = booking.user.email

    try:
        filename = await send_booking_confirmation(booking, verify_url=_verify_url(booking))
    except EmailNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured on this server. Your booking is unaffected — "
                   "you can download the confirmation PDF instead.",
        ) from exc
    except EmailDeliveryError as exc:
        # 502: the failure is upstream, not the caller's fault, and the
        # booking it refers to is still perfectly valid.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{exc} Your booking is still confirmed — you can download the confirmation PDF instead.",
        ) from exc

    return BookingEmailResponse(
        status="sent",
        recipient=mask_email(recipient),
        attachment_filename=filename,
        booking_reference=booking.reference,
    )
