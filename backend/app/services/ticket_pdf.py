"""Render an ATLAS e-ticket as an A4 PDF.

Takes a TicketData and returns bytes. Deliberately free of database access and
of any business logic, so the same function serves a browser download today
and an email attachment later:

    generate_ticket_pdf(ticket) -> bytes
            |- browser download
            `- email attachment

Typography note: the built-in PDF fonts have no rupee sign, so a Unicode font
is registered from app/assets/fonts. Without it every amount would render as a
black box.
"""
from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.services.ticket_data import TicketData

logger = logging.getLogger(__name__)

_FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
_BODY_FONT = "ATLASSans"
_BOLD_FONT = "ATLASSans-Bold"

# ATLAS brand colours, matching the frontend's --brand / --accent tokens.
_BRAND = colors.HexColor("#2563EB")
_INK = colors.HexColor("#0F172A")
_MUTED = colors.HexColor("#64748B")
_LINE = colors.HexColor("#E2E8F0")
_SUBTLE = colors.HexColor("#F8FAFC")
_WARN_BG = colors.HexColor("#FEF3C7")
_WARN_INK = colors.HexColor("#92400E")

_MARGIN = 16 * mm
_CONTENT_WIDTH = A4[0] - 2 * _MARGIN

_fonts_registered = False


def _register_fonts() -> bool:
    """Register the bundled Unicode font. Returns False if it is unavailable,
    in which case the caller falls back to Helvetica and renders 'Rs.'."""
    global _fonts_registered
    if _fonts_registered:
        return True
    regular = _FONT_DIR / "DejaVuSans.ttf"
    bold = _FONT_DIR / "DejaVuSans-Bold.ttf"
    if not regular.exists() or not bold.exists():
        logger.warning("Ticket font missing from %s; falling back to Helvetica.", _FONT_DIR)
        return False
    pdfmetrics.registerFont(TTFont(_BODY_FONT, str(regular)))
    pdfmetrics.registerFont(TTFont(_BOLD_FONT, str(bold)))
    pdfmetrics.registerFontFamily(_BODY_FONT, normal=_BODY_FONT, bold=_BOLD_FONT)
    _fonts_registered = True
    return True


def _fonts() -> tuple[str, str, bool]:
    if _register_fonts():
        return _BODY_FONT, _BOLD_FONT, True
    return "Helvetica", "Helvetica-Bold", False


def _money(amount: float, currency: str, unicode_ok: bool) -> str:
    """Indian-format an amount. Falls back to an ASCII prefix when the Unicode
    font is unavailable, rather than printing a missing-glyph box."""
    symbol = {"INR": "₹" if unicode_ok else "Rs. ", "USD": "$", "EUR": "€", "GBP": "£"}
    prefix = symbol.get(currency.upper(), f"{currency.upper()} ")
    whole = int(round(amount))
    if currency.upper() == "INR":
        # Indian digit grouping: 12,34,567
        text = str(abs(whole))
        if len(text) > 3:
            head, tail = text[:-3], text[-3:]
            groups = []
            while len(head) > 2:
                groups.insert(0, head[-2:])
                head = head[:-2]
            if head:
                groups.insert(0, head)
            text = ",".join(groups + [tail])
        formatted = f"{'-' if whole < 0 else ''}{text}"
    else:
        formatted = f"{whole:,}"
    return f"{prefix}{formatted}"


def _date(value) -> str:
    return value.strftime("%d %b %Y") if value else "—"


class _TicketDoc(BaseDocTemplate):
    """Document template that paints the brand footer on every page."""

    def __init__(self, buffer: BytesIO, ticket: TicketData, fonts: tuple[str, str, bool]):
        super().__init__(
            buffer,
            pagesize=A4,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN,
            bottomMargin=_MARGIN + 10 * mm,
            title=f"ATLAS E-Ticket {ticket.reference}",
            author="ATLAS",
            subject="Booking Confirmation",
        )
        self.ticket = ticket
        self.body_font, self.bold_font, self.unicode_ok = fonts
        frame = Frame(_MARGIN, self.bottomMargin, _CONTENT_WIDTH, A4[1] - self.bottomMargin - _MARGIN, id="body")
        self.addPageTemplates([PageTemplate(id="ticket", frames=[frame], onPage=self._footer)])

    def _footer(self, canvas, doc) -> None:
        canvas.saveState()
        y = _MARGIN + 2 * mm
        canvas.setStrokeColor(_LINE)
        canvas.setLineWidth(0.5)
        canvas.line(_MARGIN, y + 9 * mm, A4[0] - _MARGIN, y + 9 * mm)

        canvas.setFont(self.bold_font, 7.5)
        canvas.setFillColor(_INK)
        canvas.drawString(_MARGIN, y + 5 * mm, "ATLAS — Where Travel Meets AI")

        canvas.setFont(self.body_font, 7)
        canvas.setFillColor(_MUTED)
        canvas.drawString(
            _MARGIN, y + 1.8 * mm,
            "This ticket is generated by ATLAS. Verify travel details with the relevant provider before travel.",
        )
        canvas.drawRightString(A4[0] - _MARGIN, y + 5 * mm, f"Ref {self.ticket.reference}")
        canvas.drawRightString(A4[0] - _MARGIN, y + 1.8 * mm, f"Page {doc.page}")
        canvas.restoreState()


def _qr_flowable(payload: str, size_mm: float = 32) -> Drawing:
    """Vector QR, so it stays sharp when the ticket is printed."""
    widget = QrCodeWidget(payload)
    bounds = widget.getBounds()
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    target = size_mm * mm
    drawing = Drawing(target, target, transform=[target / width, 0, 0, target / height, 0, 0])
    drawing.add(widget)
    return drawing


def generate_ticket_pdf(ticket: TicketData) -> bytes:
    """Render the e-ticket and return the PDF bytes."""
    body_font, bold_font, unicode_ok = _fonts()
    buffer = BytesIO()
    doc = _TicketDoc(buffer, ticket, (body_font, bold_font, unicode_ok))

    def money(amount: float) -> str:
        return _money(amount, ticket.currency, unicode_ok)

    h1 = ParagraphStyle("h1", fontName=bold_font, fontSize=19, textColor=_INK, leading=23)
    h2 = ParagraphStyle("h2", fontName=bold_font, fontSize=11.5, textColor=_INK, leading=15, spaceBefore=6, spaceAfter=5)
    body = ParagraphStyle("body", fontName=body_font, fontSize=8.8, textColor=_INK, leading=12.5)
    muted = ParagraphStyle("muted", fontName=body_font, fontSize=7.8, textColor=_MUTED, leading=11)
    label = ParagraphStyle("label", fontName=body_font, fontSize=6.8, textColor=_MUTED, leading=9)
    value = ParagraphStyle("value", fontName=bold_font, fontSize=9.6, textColor=_INK, leading=13)
    right = ParagraphStyle("right", parent=body, alignment=TA_RIGHT)
    right_bold = ParagraphStyle("right_bold", parent=value, alignment=TA_RIGHT)

    story: list = []

    # ---------------------------------------------------------------- header
    brand = [
        Paragraph('<font color="#2563EB">ATLAS</font>', h1),
        Paragraph("WHERE TRAVEL MEETS AI", ParagraphStyle(
            "tag", fontName=body_font, fontSize=6.6, textColor=_MUTED, leading=9)),
        Spacer(1, 4),
        Paragraph("E-TICKET", ParagraphStyle(
            "et", fontName=bold_font, fontSize=12.5, textColor=_INK, leading=15)),
        Paragraph("BOOKING CONFIRMATION", ParagraphStyle(
            "bc", fontName=body_font, fontSize=8, textColor=_MUTED, leading=11)),
    ]
    status_block = [
        Paragraph("STATUS", label),
        Paragraph(ticket.status.upper(), ParagraphStyle(
            "st", fontName=bold_font, fontSize=11, textColor=_BRAND, leading=14)),
        Spacer(1, 4),
        Paragraph("BOOKING REFERENCE", label),
        Paragraph(ticket.reference, ParagraphStyle(
            "ref", fontName=bold_font, fontSize=13, textColor=_INK, leading=16)),
    ]
    header = Table([[brand, status_block]], colWidths=[_CONTENT_WIDTH * 0.58, _CONTENT_WIDTH * 0.42])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [header, Spacer(1, 8)]

    rule = Table([[""]], colWidths=[_CONTENT_WIDTH], rowHeights=[2])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _BRAND)]))
    story += [rule, Spacer(1, 9)]

    # The single most important disclosure on the document.
    if ticket.is_mock:
        banner = Table(
            [[Paragraph(
                "<b>DEMO / MOCK BOOKING</b> &nbsp;—&nbsp; No payment was processed and no external "
                "reservation has been created. This document is an ATLAS booking record only.",
                ParagraphStyle("warn", fontName=body_font, fontSize=8.2, textColor=_WARN_INK, leading=11.5))]],
            colWidths=[_CONTENT_WIDTH],
        )
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _WARN_BG),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#FCD34D")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story += [banner, Spacer(1, 10)]

    # -------------------------------------------------- booking + QR + trip
    def field_pair(name: str, text: str):
        return [Paragraph(name, label), Paragraph(text, value), Spacer(1, 5)]

    booking_facts = [
        *field_pair("BOOKING ID", ticket.booking_id[:8].upper()),
        *field_pair("BOOKED ON", ticket.booked_at.strftime("%d %b %Y, %H:%M")),
        *field_pair("PAYMENT STATUS", "Not charged (demo)" if ticket.is_mock else "Paid"),
        *field_pair("TRIP TYPE", ticket.booking_type),
    ]
    journey_facts = [
        *field_pair("DESTINATION", ticket.destination or ticket.title),
        *field_pair(
            "TRAVEL DATES",
            f"{_date(ticket.start_date)} — {_date(ticket.end_date)}"
            if ticket.start_date else _date(ticket.travel_date),
        ),
        *field_pair("DURATION", ticket.duration_label or "—"),
        *field_pair("TRAVELLERS", f"{ticket.travelers} Traveller{'s' if ticket.travelers != 1 else ''}"),
    ]
    qr_payload = ticket.verify_url or f"ATLAS:{ticket.reference}"
    qr_block = [
        _qr_flowable(qr_payload),
        Spacer(1, 3),
        Paragraph("Scan to view booking", ParagraphStyle(
            "qr", parent=muted, alignment=1, fontSize=7.2)),
    ]

    summary = Table(
        [[booking_facts, journey_facts, qr_block]],
        colWidths=[_CONTENT_WIDTH * 0.32, _CONTENT_WIDTH * 0.38, _CONTENT_WIDTH * 0.30],
    )
    summary.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.6, _LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, _LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [summary, Spacer(1, 12)]

    # ------------------------------------------------------------ travellers
    story.append(Paragraph("Traveller Details", h2))
    if ticket.lead_traveler_name:
        rows = [[
            Paragraph("<b>#</b>", body), Paragraph("<b>Name</b>", body),
            Paragraph("<b>Type</b>", body), Paragraph("<b>Contact</b>", body),
        ]]
        contact = " · ".join(p for p in (ticket.lead_traveler_email, ticket.lead_traveler_phone) if p)
        rows.append([
            Paragraph("1", body),
            Paragraph(ticket.lead_traveler_name, body),
            Paragraph("Lead traveller", body),
            Paragraph(contact or "—", body),
        ])
        # Only the lead traveller's details are collected by the booking flow;
        # the others are counted, not named. Inventing names would be worse.
        if ticket.travelers > 1:
            rows.append([
                Paragraph("2–%d" % ticket.travelers, body),
                Paragraph("Not provided", muted),
                Paragraph("Adult", body),
                Paragraph("—", muted),
            ])
        table = Table(rows, colWidths=[_CONTENT_WIDTH * 0.08, _CONTENT_WIDTH * 0.32,
                                       _CONTENT_WIDTH * 0.22, _CONTENT_WIDTH * 0.38])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _SUBTLE),
            ("BOX", (0, 0), (-1, -1), 0.6, _LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, _LINE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(table)
    else:
        story.append(Paragraph(
            f"{ticket.travelers} traveller(s). Names were not captured for this booking.", muted))
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------- fare summary
    story.append(Paragraph("Fare Summary", h2))
    fare_rows = [[Paragraph("<b>Category</b>", body), Paragraph("<b>Amount</b>", right)]]
    if ticket.fare_breakdown and ticket.itinerary_total:
        for name, amount in ticket.fare_breakdown:
            fare_rows.append([Paragraph(name, body), Paragraph(money(amount), right)])
        fare_rows.append([Paragraph("Itinerary estimate", body),
                          Paragraph(money(ticket.itinerary_total), right)])
    fare_rows.append([Paragraph("<b>Booking total</b>", value),
                      Paragraph(f"<b>{money(ticket.total_price)}</b>", right_bold)])
    fare = Table(fare_rows, colWidths=[_CONTENT_WIDTH * 0.68, _CONTENT_WIDTH * 0.32])
    fare.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _SUBTLE),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFF6FF")),
        ("BOX", (0, 0), (-1, -1), 0.6, _LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(fare)

    if ticket.budget is not None and ticket.itinerary_total is not None:
        remaining = ticket.remaining_budget
        story += [Spacer(1, 6), Paragraph(
            f"Trip budget {money(ticket.budget)} &nbsp;·&nbsp; "
            f"Estimated total {money(ticket.itinerary_total)} &nbsp;·&nbsp; "
            f"Remaining {money(remaining if remaining is not None else 0)}", muted)]

    # ================================================================ page 2
    story.append(PageBreak())

    if ticket.days:
        story.append(Paragraph("Itinerary Summary", h2))
        for day in ticket.days:
            rows = [[
                Paragraph(f"<b>Day {day.day_number} — {day.title}</b>", body),
                Paragraph(f"<b>{_date(day.date)}</b>", right),
            ]]
            head = Table(rows, colWidths=[_CONTENT_WIDTH * 0.7, _CONTENT_WIDTH * 0.3])
            head.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _SUBTLE),
                ("BOX", (0, 0), (-1, -1), 0.5, _LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]))
            detail_rows = [[
                Paragraph(a.time, muted),
                Paragraph(a.description, body),
                Paragraph(a.location, muted),
                Paragraph(money(a.cost) if a.cost else "—", right),
            ] for a in day.activities]
            block = [head]
            if detail_rows:
                detail = Table(detail_rows, colWidths=[
                    _CONTENT_WIDTH * 0.10, _CONTENT_WIDTH * 0.45,
                    _CONTENT_WIDTH * 0.30, _CONTENT_WIDTH * 0.15])
                detail.setStyle(TableStyle([
                    ("BOX", (0, 0), (-1, -1), 0.5, _LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, _LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ]))
                block.append(detail)
            block.append(Spacer(1, 7))
            # Keep a day's heading with at least its first rows.
            story.append(KeepTogether(block))
        story.append(Spacer(1, 4))

    # -------------------------------------------- accommodation & transport
    story.append(Paragraph("Accommodation", h2))
    stays = [a for day in ticket.days for a in day.activities if a.category == "accommodation"]
    if stays:
        story.append(Paragraph(
            f"<b>AI Estimate / Suggested Accommodation</b> — {stays[0].location}. "
            f"{ticket.nights or 0} night(s), check-in {_date(ticket.start_date)}, "
            f"check-out {_date(ticket.end_date)}.", body))
        story.append(Paragraph(
            "This is a suggestion generated by ATLAS, not a confirmed hotel reservation. "
            "No property has been contacted or booked.", muted))
    else:
        story.append(Paragraph("No accommodation is recorded for this booking.", muted))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Transportation", h2))
    legs = [a for day in ticket.days for a in day.activities if a.category == "travel"]
    if legs:
        story.append(Paragraph("<b>Estimated Transportation</b>", body))
        rows = [[Paragraph("<b>Leg</b>", body), Paragraph("<b>Route</b>", body),
                 Paragraph("<b>Estimated fare</b>", right)]]
        for leg in legs[:8]:
            rows.append([Paragraph(leg.description, body), Paragraph(leg.location, muted),
                         Paragraph(money(leg.cost) if leg.cost else "—", right)])
        table = Table(rows, colWidths=[_CONTENT_WIDTH * 0.42, _CONTENT_WIDTH * 0.38, _CONTENT_WIDTH * 0.20])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _SUBTLE),
            ("BOX", (0, 0), (-1, -1), 0.6, _LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, _LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        story += [table, Spacer(1, 4), Paragraph(
            "No seats, PNRs, operators or service numbers have been reserved — ATLAS holds none "
            "for this booking, and none are shown.", muted)]
    else:
        story.append(Paragraph("No transportation is recorded for this booking.", muted))
    story.append(Spacer(1, 10))

    # ----------------------------------------------------- data transparency
    if ticket.data_sources:
        story.append(Paragraph("Data Information", h2))
        rows = [[Paragraph(name, body), Paragraph(state, right)] for name, state in ticket.data_sources]
        table = Table(rows, colWidths=[_CONTENT_WIDTH * 0.45, _CONTENT_WIDTH * 0.55])
        table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, _LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, _LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        story += [table, Spacer(1, 10)]

    # ------------------------------------------------------------ the rules
    story.append(Paragraph("Important Information", h2))
    notes = [
        "Please verify all travel details before departure.",
        "Times, prices and availability are estimates and may change.",
        "AI-generated recommendations should be independently verified.",
        "Accommodation and transportation marked as estimates are not confirmed reservations.",
        "This document represents the ATLAS booking record.",
    ]
    if ticket.is_mock:
        notes.append("This is a mock booking: no real payment was taken and no external reservation exists.")
    for note in notes:
        story.append(Paragraph(f"• &nbsp;{note}", muted))

    story += [Spacer(1, 9), Paragraph("Cancellation &amp; Modification", h2), Paragraph(
        "Cancellation and modification policies depend on the underlying travel provider. "
        "ATLAS holds no provider reservation for this booking, so no provider policy applies to it.", muted)]

    story += [Spacer(1, 10), Paragraph(
        f"Generated on: {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC", muted)]

    doc.build(story)
    return buffer.getvalue()
