"""Outbound email for ATLAS, over SMTP.

Why SMTP rather than the Gmail API: ATLAS authenticates users with a password
as well as with Google, and the stored OAuth flow keeps no refresh token, so
Gmail-on-behalf-of-the-user could only ever reach a subset of users. It would
also send *as the traveller*, putting a system notification in their own Sent
folder. A booking confirmation comes from ATLAS, so it is sent from an ATLAS
mailbox.

Deliberately the standard library: one message with one attachment does not
justify a framework.

This module does not know what a booking is. It takes a recipient, a subject,
two body parts and optional attachment bytes — so the PDF it attaches is
whatever the caller already generated, never something regenerated here.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

# Connect, TLS and auth against Gmail measure ~2s; the rest is uploading the
# e-ticket attachment, which took ~25s on a real send from a domestic
# connection. A 20s socket budget left almost no margin, so a correctly
# configured sender could still fail intermittently on a slower link.
_TIMEOUT_SECONDS = 45

# Outer ceiling for the whole send, including PDF handover. Kept above the
# socket budget so a stalled transfer surfaces as a socket error (which names
# the cause) rather than a bare timeout.
_OVERALL_TIMEOUT_SECONDS = 60


class EmailNotConfiguredError(RuntimeError):
    """No SMTP settings are present. A deployment choice, not a user error."""


class EmailDeliveryError(RuntimeError):
    """The provider refused or could not be reached."""


@dataclass
class Attachment:
    filename: str
    content: bytes
    mime_type: str = "application/pdf"


def is_configured() -> bool:
    """Whether outbound email is usable at all.

    The UI asks this so it can hide the email action on a deployment with no
    mail configured, rather than offering a button that always fails.
    """
    return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)


def mask_email(address: str) -> str:
    """`aditya@example.com` -> `ad****@example.com`.

    Used in logs and in API responses: enough for a person to recognise their
    own address, not enough to harvest from a log file.
    """
    local, _, domain = address.partition("@")
    if not domain:
        return "***"
    head = local[:2] if len(local) > 2 else local[:1]
    return f"{head}{'*' * max(2, len(local) - len(head))}@{domain}"


def _auth_failure_hint() -> str:
    """Explain a rejected sender credential in terms of the fix.

    Gmail stopped accepting ordinary account passwords over SMTP in 2022, so
    a plain password is the overwhelmingly common cause. An App Password is
    always 16 characters, which is cheap to check and worth saying out loud.
    """
    base = "The mail server rejected the ATLAS sender credentials."
    host = (settings.SMTP_HOST or "").lower()
    if "gmail" in host or "googlemail" in host:
        if len(settings.SMTP_PASSWORD) != 16:
            return (
                f"{base} Gmail needs a 16-character App Password (2-Step Verification must be on); "
                "the configured SMTP_PASSWORD is not 16 characters, so it looks like a normal "
                "account password."
            )
        return f"{base} Check that SMTP_USERNAME and the App Password belong to the same Google account."
    return base


def _build_message(
    *,
    to_address: str,
    subject: str,
    text_body: str,
    html_body: str,
    attachment: Attachment | None,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_address
    # Plain text first, HTML as the richer alternative — clients that block
    # HTML still get a readable confirmation.
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    if attachment is not None:
        maintype, _, subtype = attachment.mime_type.partition("/")
        message.add_attachment(
            attachment.content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=attachment.filename,
        )
    return message


def _send_blocking(message: EmailMessage) -> None:
    """smtplib is synchronous; callers run this off the event loop."""
    context = ssl.create_default_context()
    if settings.SMTP_USE_SSL:
        with smtplib.SMTP_SSL(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=_TIMEOUT_SECONDS, context=context
        ) as server:
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
        return

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=_TIMEOUT_SECONDS) as server:
        if settings.SMTP_USE_TLS:
            server.starttls(context=context)
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)


async def send_email(
    *,
    to_address: str,
    subject: str,
    text_body: str,
    html_body: str,
    attachment: Attachment | None = None,
) -> None:
    """Send one message. Raises EmailNotConfiguredError or EmailDeliveryError.

    Never logs the recipient in full, the message body, or the attachment —
    only whether it went out.
    """
    if not is_configured():
        raise EmailNotConfiguredError("Outbound email is not configured on this server.")

    message = _build_message(
        to_address=to_address,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        attachment=attachment,
    )

    try:
        # Keeps a slow or hung SMTP server from blocking the whole event loop.
        await asyncio.wait_for(asyncio.to_thread(_send_blocking, message), timeout=_OVERALL_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        logger.warning("Email to %s timed out.", mask_email(to_address))
        raise EmailDeliveryError("The mail server did not respond in time.") from exc
    except smtplib.SMTPAuthenticationError as exc:
        # Log the server's own rejection. It names the cause (Gmail's 535
        # points at its BadCredentials help page) and contains no secret —
        # without it, a misconfigured sender is a silent mystery. The
        # credential itself is still never logged.
        detail = exc.smtp_error.decode(errors="replace") if isinstance(exc.smtp_error, bytes) else str(exc.smtp_error)
        logger.error(
            "SMTP rejected the ATLAS sender credentials for %s (code %s): %s",
            settings.SMTP_HOST, exc.smtp_code, detail.strip(),
        )
        raise EmailDeliveryError(_auth_failure_hint()) from exc
    except smtplib.SMTPRecipientsRefused as exc:
        logger.warning("SMTP refused recipient %s.", mask_email(to_address))
        raise EmailDeliveryError("The mail server refused the recipient address.") from exc
    except (smtplib.SMTPException, OSError, ssl.SSLError) as exc:
        logger.warning("Email to %s failed: %s", mask_email(to_address), type(exc).__name__)
        raise EmailDeliveryError("The mail server could not be reached.") from exc

    logger.info("Confirmation email sent to %s.", mask_email(to_address))
