import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class LostFoundReport(Base):
    """A lost or found item reported on the community board.

    Reports are readable by any signed-in traveller — that is the point of the
    board — but only the reporter owns the row. `user_id` is always taken from
    the authenticated session, never from the request body.

    `image_url` holds a path to a file on disk, not the image itself: photo
    bytes do not belong in Postgres.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    title = Column(String, nullable=False)
    report_type = Column(String, nullable=False)  # "lost" | "found"
    category = Column(String, nullable=False)
    location = Column(String, nullable=False)
    reported_date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    contact = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Open")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="lost_found_reports")

    __table_args__ = (
        # The board is browsed newest-first.
        Index("ix_lost_found_report_created_at", "created_at"),
    )
