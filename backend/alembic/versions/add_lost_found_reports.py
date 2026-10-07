"""Persist Lost & Found reports.

Reports previously existed only in browser state and disappeared on refresh,
which makes a community board useless.

Revision ID: add_lost_found_reports
Revises: add_trip_data_context
Create Date: 2026-09-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "add_lost_found_reports"
down_revision: Union[str, None] = "add_trip_data_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lost_found_report",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("reported_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        # A path to a file on disk. Photo bytes are never stored in the row.
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("contact", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="Open"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lost_found_report_created_at", "lost_found_report", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_lost_found_report_created_at", table_name="lost_found_report")
    op.drop_table("lost_found_report")
