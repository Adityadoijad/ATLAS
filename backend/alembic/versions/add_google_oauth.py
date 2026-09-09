"""Add Google OAuth support to User model.

Revision ID: add_google_oauth
Revises: 0bc76a73d6ce
Create Date: 2026-09-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_google_oauth"
down_revision: Union[str, None] = "0bc76a73d6ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make password_hash nullable for OAuth-only users
    op.alter_column("user", "password_hash", nullable=True)

    # Add google_id column for Google OAuth
    op.add_column("user", sa.Column("google_id", sa.String(), nullable=True))
    op.create_index("ix_user_google_id", "user", ["google_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_google_id", table_name="user")
    op.drop_column("user", "google_id")
    op.alter_column("user", "password_hash", nullable=False)
