"""Persist where the traveller's journey begins.

The itinerary previously started at the first planned activity, so the first
route leg was whatever the AI happened to schedule first — never the station
or airport the traveller actually departs from. Recording the boarding
location makes that first leg real, and makes it survive a page refresh.

Revision ID: add_trip_boarding_location
Revises: add_lost_found_reports
Create Date: 2026-09-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_trip_boarding_location"
down_revision: Union[str, None] = "add_lost_found_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, and deliberately left so. Every trip that already exists was
    # planned without a boarding location; back-filling one — from the
    # destination, the user's profile, anywhere — would put a journey on their
    # itinerary that they never told us about. Those trips render exactly as
    # they did before, starting at their first planned stop.
    op.add_column("trip", sa.Column("boarding_location", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("trip", "boarding_location")
