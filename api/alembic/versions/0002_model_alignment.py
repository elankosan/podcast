"""Align database schema with current SQLAlchemy models.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-24 18:12:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.String(), nullable=True, server_default="true"))
    op.add_column("users", sa.Column("last_login", sa.DateTime(), nullable=True))

    op.add_column("podcasts", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.add_column("episodes", sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_episodes_current_version_id_versions",
        "episodes",
        "versions",
        ["current_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_episodes_current_version_id_versions", "episodes", type_="foreignkey")
    op.drop_column("episodes", "current_version_id")
    op.drop_column("podcasts", "updated_at")
    op.drop_column("users", "last_login")
    op.drop_column("users", "is_active")
