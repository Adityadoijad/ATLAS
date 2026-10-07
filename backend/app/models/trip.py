import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Date, Float, Integer, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base

class Trip(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    travelers = Column(Integer, default=1, nullable=False)
    budget = Column(Float, nullable=True)
    preferences = Column(JSON, nullable=False, default=dict)
    currency = Column(String, default="USD", nullable=False)
    # "upcoming" or "past". The stored value is a starting point only:
    # TripResponse derives the date-driven state on read, because a column
    # written once at creation goes stale the day the trip ends. The default
    # previously disagreed with what the planner writes ("planning" vs
    # "upcoming"), which put trips created through /trips in a third state
    # nothing handled.
    status = Column(String, default="upcoming", nullable=False)
    # Per-agent live/estimated flags captured when the plan was generated.
    # Persisted so an e-ticket issued later can state which parts were live
    # data and which were AI estimates instead of guessing after the fact.
    # Null on trips created before this was recorded — the ticket omits the
    # section rather than inventing it.
    data_context = Column(JSON, nullable=True)
    # Where the traveller's journey starts: {name, display_name, latitude,
    # longitude}. Nullable because trips created before this feature have no
    # boarding location, and inventing one for them would put a route leg on
    # the itinerary that the user never asked for.
    boarding_location = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="trips")
    itinerary_days = relationship("ItineraryDay", back_populates="trip", cascade="all, delete-orphan", order_by="ItineraryDay.day_number")

    __table_args__ = (
        Index("ix_trip_user_created_at", "user_id", "created_at"),
    )
