"""Compose and send the booking confirmation email.

The seam that matters:

    Booking -> build_ticket -> generate_ticket_pdf -> bytes
                                                       |- browser download
                                                       `- this attachment

The PDF is produced by the same two calls the download endpoint makes, so the
attachment is byte-for-byte the document the user can download. Nothing about
the ticket's layout or data mapping is repeated here.
"""
from __future__ import annotations

from app.models.booking import Booking
from app.services.email_service import Attachment, send_email
from app.services.ticket_data import TicketData, build_ticket
from app.services.ticket_pdf import generate_ticket_pdf

ATTACHMENT_NAME_TEMPLATE = "ATLAS_Booking_Confirmation_{reference}.pdf"


def attachment_filename(reference: str) -> str:
    return ATTACHMENT_NAME_TEMPLATE.format(reference=reference)


def subject_for(reference: str) -> str:
    return f"ATLAS Booking Confirmation — {reference}"


def _date(value) -> str:
    return value.strftime("%d %b %Y") if value else "—"


def _travel_window(ticket: TicketData) -> str:
    if ticket.start_date and ticket.end_date:
        return f"{_date(ticket.start_date)} — {_date(ticket.end_date)}"
    return _date(ticket.travel_date)


def _text_body(ticket: TicketData, name: str) -> str:
    lines = [
        f"Hi {name},",
        "",
        "Your ATLAS booking is confirmed. The full e-ticket is attached as a PDF.",
        "",
        f"Booking reference : {ticket.reference}",
        f"Destination       : {ticket.destination or ticket.title}",
        f"Travel dates      : {_travel_window(ticket)}",
        f"Travellers        : {ticket.travelers}",
        f"Booking total     : {ticket.currency} {int(round(ticket.total_price)):,}",
    ]
    if ticket.is_mock:
        lines += [
            "",
            "Please note: this is a demo booking. No payment was taken and no",
            "reservation has been made with any travel provider.",
        ]
    lines += [
        "",
        "Verify all travel details with the relevant provider before you travel.",
        "",
        "ATLAS — Where Travel Meets AI",
    ]
    return "\n".join(lines)


def _html_body(ticket: TicketData, name: str) -> str:
    """Inline styles only — mail clients strip stylesheets."""
    mock_notice = (
        '<p style="margin:16px 0 0;padding:12px 14px;background:#FEF3C7;border:1px solid #FCD34D;'
        'border-radius:8px;color:#92400E;font-size:13px;line-height:1.5;">'
        "<strong>Demo booking.</strong> No payment was taken and no reservation has been made "
        "with any travel provider.</p>"
        if ticket.is_mock
        else ""
    )
    rows = "".join(
        '<tr>'
        f'<td style="padding:7px 0;color:#64748B;font-size:13px;">{label}</td>'
        f'<td style="padding:7px 0;color:#0F172A;font-size:13px;font-weight:600;text-align:right;">{value}</td>'
        '</tr>'
        for label, value in (
            ("Booking reference", ticket.reference),
            ("Destination", ticket.destination or ticket.title),
            ("Travel dates", _travel_window(ticket)),
            ("Travellers", str(ticket.travelers)),
            ("Booking total", f"{ticket.currency} {int(round(ticket.total_price)):,}"),
        )
    )
    return f"""\
<!doctype html>
<html><body style="margin:0;padding:24px;background:#F8FAFC;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:26px;">
    <p style="margin:0;font-size:21px;font-weight:700;color:#2563EB;letter-spacing:-0.3px;">ATLAS</p>
    <p style="margin:2px 0 20px;font-size:10px;letter-spacing:1.4px;color:#64748B;text-transform:uppercase;">
      Where Travel Meets AI</p>

    <h1 style="margin:0 0 6px;font-size:17px;color:#0F172A;">Your booking is confirmed</h1>
    <p style="margin:0 0 18px;font-size:13.5px;color:#475569;line-height:1.55;">
      Hi {name}, your ATLAS e-ticket is attached to this email as a PDF.</p>

    <table style="width:100%;border-collapse:collapse;border-top:1px solid #E2E8F0;">{rows}</table>
    {mock_notice}

    <p style="margin:18px 0 0;font-size:12.5px;color:#64748B;line-height:1.55;">
      Verify all travel details with the relevant provider before you travel.</p>
    <p style="margin:18px 0 0;padding-top:14px;border-top:1px solid #E2E8F0;font-size:11.5px;color:#94A3B8;">
      ATLAS — Where Travel Meets AI</p>
  </div>
</body></html>"""


async def send_booking_confirmation(booking: Booking, *, verify_url: str | None = None) -> str:
    """Email the booking's confirmation with its e-ticket attached.

    Returns the attachment filename. Raises EmailNotConfiguredError or
    EmailDeliveryError — the caller is responsible for making sure neither
    ever disturbs the booking itself.

    The recipient is the owning account's email, read from the database.
    It is never taken from the request.
    """
    ticket = build_ticket(booking, verify_url=verify_url)
    pdf = generate_ticket_pdf(ticket)

    recipient = booking.user.email
    display_name = (booking.lead_traveler_name or booking.user.name or "traveller").split(" ")[0]
    filename = attachment_filename(booking.reference)

    await send_email(
        to_address=recipient,
        subject=subject_for(booking.reference),
        text_body=_text_body(ticket, display_name),
        html_body=_html_body(ticket, display_name),
        attachment=Attachment(filename=filename, content=pdf, mime_type="application/pdf"),
    )
    return filename
