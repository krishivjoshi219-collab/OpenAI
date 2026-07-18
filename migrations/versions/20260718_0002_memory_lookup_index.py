"""Add an efficient business-memory category lookup index.

Revision ID: 20260718_0002
Revises: 20260718_0001
Create Date: 2026-07-18 00:10:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260718_0002"
down_revision: str | None = "20260718_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the composite index used by business-scoped memory retrieval."""

    op.create_index(
        "ix_business_memories_business_category",
        "business_memories",
        ["business_id", "category"],
    )


def downgrade() -> None:
    """Remove the business-memory lookup index."""

    op.drop_index("ix_business_memories_business_category", table_name="business_memories")
