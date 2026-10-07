from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ReportType = Literal["lost", "found"]
ReportStatus = Literal["Open", "Matched", "Resolved"]


class LostFoundCreate(BaseModel):
    """A new report. Note there is deliberately no user_id: ownership comes
    from the authenticated session, never from the request body."""

    title: str = Field(min_length=1, max_length=200)
    report_type: ReportType
    category: str = Field(min_length=1, max_length=60)
    location: str = Field(min_length=1, max_length=200)
    reported_date: date
    description: str = Field(min_length=1, max_length=1000)
    contact: str = Field(min_length=1, max_length=60)
    # Base64 data URL of the reporter's own photo, written to disk on create.
    # None simply means no photo was attached.
    image_data_url: str | None = Field(default=None, max_length=6_000_000)


class LostFoundResponse(BaseModel):
    """What the board shows. Carries no contact details or identity of the
    reporter beyond the contact *preference* they chose to publish."""

    id: UUID
    title: str
    report_type: ReportType
    category: str
    location: str
    reported_date: date
    description: str
    image_url: str | None = None
    contact: str
    status: str
    created_at: datetime
    # Lets the UI tell the signed-in reporter's own entries apart without
    # revealing who posted anything else.
    is_mine: bool = False

    class Config:
        from_attributes = True
