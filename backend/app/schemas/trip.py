from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import UUID
from datetime import date, datetime
from typing import Any, List, Optional
from app.schemas.itinerary import ItineraryDayResponse
from app.schemas.planner import BoardingLocation

class TripBase(BaseModel):
    title: str
    destination: str
    start_date: date
    end_date: date
    travelers: int = 1
    budget: Optional[float] = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    currency: str = "USD"
    status: str = "planning"
    # Null on every trip planned before this existed, and on trips created
    # through the plain /trips endpoint. The itinerary handles that by starting
    # at the first planned stop, exactly as it always did.
    boarding_location: Optional[BoardingLocation] = None

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    title: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: Optional[int] = None
    budget: Optional[float] = None
    preferences: Optional[dict[str, Any]] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    boarding_location: Optional[BoardingLocation] = None

class TripResponse(TripBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    itinerary_days: List[ItineraryDayResponse] = []
    data_context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _derive_status_from_dates(self) -> "TripResponse":
        """A trip whose end date has passed is past, whatever the column says.

        The stored value was written once at creation and never revisited, so
        every trip stayed "upcoming" for ever and the dashboard's completed
        count could only ever be zero. Deriving it on read keeps that correct
        without a scheduler, and without a migration that would go stale again
        the day after it ran.

        A status the user set deliberately ("cancelled") is left alone — this
        only decides between the two date-driven states.
        """
        if self.status in {"cancelled", "archived"}:
            return self
        if self.end_date is None:
            return self
        # Purely date-driven, so the stored value cannot disagree with the
        # calendar. This also normalises the schema's legacy "planning"
        # default, which no client rendered as a distinct state.
        self.status = "past" if self.end_date < date.today() else "upcoming"
        return self

    @field_validator("data_context", mode="before")
    @classmethod
    def _default_empty_context(cls, value: object) -> object:
        """Trips created outside the planner (and any created before the column
        existed) have no recorded provenance. Keep the response contract an
        object rather than leaking null to clients that already treat this as
        a dict."""
        return {} if value is None else value

    class Config:
        from_attributes = True
