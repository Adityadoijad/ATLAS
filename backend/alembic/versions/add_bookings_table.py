"""Persist bookings so an e-ticket can be issued for them.

Bookings previously existed only in browser state, which meant a booking
reference changed on every reload and no booking could be owned, verified or
re-downloaded. The e-ticket needs a stable, owned record.

Revision ID: add_bookings_table
Revises: add_google_oauth
Create Date: 2026-09-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "add_bookings_table"
down_revision: Union[str, None] = "add_google_oauth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("booking_type", sa.String(), nullable=False, server_default="Package"),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(), nullable=False, server_default="INR"),
        sa.Column("travelers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="upcoming"),
        sa.Column("lead_traveler_name", sa.String(), nullable=True),
        sa.Column("lead_traveler_email", sa.String(), nullable=True),
        sa.Column("lead_traveler_phone", sa.String(), nullable=True),
        sa.Column("id_document_type", sa.String(), nullable=True),
        sa.Column("is_mock", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        # A deleted trip must not take its booking with it; the booking record stands.
        sa.ForeignKeyConstraint(["trip_id"], ["trip.id"], ondelete="SET NULL"),
    )
    # The reference is printed on the ticket and encoded in its QR code, so it
    # has to be unique for lookups to be unambiguous.
    op.create_index("ix_booking_reference", "booking", ["reference"], unique=True)
    op.create_index("ix_booking_user_created_at", "booking", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_booking_user_created_at", table_name="booking")
    op.drop_index("ix_booking_reference", table_name="booking")
    op.drop_table("booking")
