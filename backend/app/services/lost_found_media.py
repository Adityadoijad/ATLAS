"""Store Lost & Found photos as files, not database rows.

The browser downsizes a chosen photo and sends it as a data URL. This decodes
that once, writes the bytes under the uploads directory, and returns a public
path for the row — so Postgres holds a reference and the image lives on disk.

Everything here treats the payload as hostile: the format is checked against
the actual file signature rather than the declared type, the size is capped,
and the filename is generated server-side so a caller can never steer the
write outside the uploads directory.
"""
from __future__ import annotations

import base64
import binascii
import logging
import re
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# backend/uploads/lost-found
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
LOST_FOUND_DIR = UPLOAD_ROOT / "lost-found"
PUBLIC_PREFIX = "/uploads/lost-found"

_DATA_URL_RE = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,(.+)$", re.DOTALL)

# The client downscales to roughly 15-60 KB. This ceiling is generous enough
# for an un-downscaled phone photo while refusing anything absurd.
MAX_IMAGE_BYTES = 3 * 1024 * 1024

# Real file signatures, so a PNG renamed as JPEG (or a script with an image
# mime type) cannot get written.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"RIFF", ".webp"),
)


class InvalidImageError(ValueError):
    """The payload is not a usable image."""


def _extension_for(payload: bytes) -> str:
    for signature, extension in _SIGNATURES:
        if payload.startswith(signature):
            # WEBP is "RIFF....WEBP"; check the second marker too.
            if extension == ".webp" and payload[8:12] != b"WEBP":
                continue
            return extension
    raise InvalidImageError("The uploaded file is not a supported image.")


def save_data_url(data_url: str) -> str:
    """Write a base64 image data URL to disk and return its public path.

    Raises InvalidImageError for anything that is not a small, real image.
    """
    match = _DATA_URL_RE.match((data_url or "").strip())
    if not match:
        raise InvalidImageError("Expected a base64-encoded JPEG, PNG or WEBP data URL.")

    try:
        payload = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidImageError("The image data could not be decoded.") from exc

    if not payload:
        raise InvalidImageError("The image is empty.")
    if len(payload) > MAX_IMAGE_BYTES:
        raise InvalidImageError("The image is larger than 3 MB.")

    extension = _extension_for(payload)
    # Server-generated name: the caller never influences the write path.
    filename = f"{uuid.uuid4().hex}{extension}"
    LOST_FOUND_DIR.mkdir(parents=True, exist_ok=True)
    (LOST_FOUND_DIR / filename).write_bytes(payload)

    logger.info("Stored a Lost & Found photo (%d bytes).", len(payload))
    return f"{PUBLIC_PREFIX}/{filename}"


def delete_stored_image(public_path: str | None) -> None:
    """Remove a previously stored photo, ignoring anything outside uploads."""
    if not public_path or not public_path.startswith(f"{PUBLIC_PREFIX}/"):
        return
    candidate = (LOST_FOUND_DIR / Path(public_path).name).resolve()
    try:
        # Guards against a stored path that somehow escapes the directory.
        candidate.relative_to(LOST_FOUND_DIR.resolve())
    except ValueError:
        return
    candidate.unlink(missing_ok=True)
