from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from typing import Any, List, Optional
from app.schemas.itinerary import ItineraryDayResponse

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

class TripResponse(TripBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    itinerary_days: List[ItineraryDayResponse] = []
    data_context: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True
