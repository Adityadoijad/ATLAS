"""Persist the planner's per-agent live/estimate flags on the trip.

The e-ticket has to state which information was live and which was an AI
estimate. Those flags were previously returned to the browser and discarded,
so a ticket issued later had nothing truthful to report.

Revision ID: add_trip_data_context
Revises: add_bookings_table
Create Date: 2026-09-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_trip_data_context"
down_revision: Union[str, None] = "add_bookings_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: trips generated before this column existed simply have no
    # recorded provenance, and the ticket omits the section for them.
    op.add_column("trip", sa.Column("data_context", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("trip", "data_context")
