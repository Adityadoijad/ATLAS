import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Booking(Base):
    """A booking record owned by one user.

    ATLAS bookings are simulations: no payment is taken and no external
    provider is contacted. `is_mock` records that on the row itself rather
    than being assumed at render time, so a real provider integration later
    can persist alongside these without the e-ticket mislabelling either.

    `reference` is assigned once, at creation, and never regenerated — the
    e-ticket, the QR code and the user's records must all agree forever.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    # Optional: a booking made from a generated itinerary links back to it so
    # the e-ticket can show the day-by-day plan. Set null rather than deleting
    # the booking if the trip goes away — the booking record still stands.
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trip.id", ondelete="SET NULL"), nullable=True)

    reference = Column(String, nullable=False, unique=True, index=True)
    title = Column(String, nullable=False)
    booking_type = Column(String, nullable=False, default="Package")
    travel_date = Column(Date, nullable=False)
    price = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="INR")
    travelers = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="upcoming")

    # Lead traveller details captured by the booking flow.
    lead_traveler_name = Column(String, nullable=True)
    lead_traveler_email = Column(String, nullable=True)
    lead_traveler_phone = Column(String, nullable=True)
    id_document_type = Column(String, nullable=True)

    is_mock = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="bookings")
    trip = relationship("Trip")

    __table_args__ = (
        Index("ix_booking_user_created_at", "user_id", "created_at"),
    )
