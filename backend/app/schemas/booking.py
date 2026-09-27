from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.validators import coerce_numeric_cost

BookingType = Literal["Flight", "Hotel", "Activity", "Package"]
BookingStatus = Literal["upcoming", "completed", "cancelled"]


class BookingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    booking_type: BookingType = "Package"
    travel_date: date
    price: float = Field(ge=0)
    travelers: int = Field(ge=1, le=50)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    # Optional link to the generated itinerary this booking came from, so the
    # e-ticket can print the real day-by-day plan.
    trip_id: UUID | None = None
    lead_traveler_name: str | None = Field(default=None, max_length=200)
    lead_traveler_email: str | None = Field(default=None, max_length=320)
    lead_traveler_phone: str | None = Field(default=None, max_length=50)
    id_document_type: str | None = Field(default=None, max_length=50)

    @field_validator("price", mode="before")
    @classmethod
    def _normalize_price(cls, value: object) -> object:
        return coerce_numeric_cost(value)


class BookingResponse(BaseModel):
    id: UUID
    reference: str
    title: str
    booking_type: str
    travel_date: date
    price: float
    currency: str
    travelers: int
    status: str
    trip_id: UUID | None = None
    is_mock: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EmailCapability(BaseModel):
    """Whether this deployment can send email, so the UI can hide the action
    rather than offering one that is certain to fail."""

    available: bool


class BookingEmailResponse(BaseModel):
    status: Literal["sent"]
    # Masked: enough for the user to recognise their own address, not enough
    # to harvest from a log or a shared screen.
    recipient: str
    attachment_filename: str
    booking_reference: str
