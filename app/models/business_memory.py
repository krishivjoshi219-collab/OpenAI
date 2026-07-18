"""Business-scoped durable memory model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDTimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business


class BusinessMemory(UUIDTimestampMixin, Base):
    """A durable operational fact or preference tied to a business."""

    __tablename__ = "business_memories"
    __table_args__ = (Index("ix_business_memories_business_category", "business_id", "category"),)

    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(100))
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    business: Mapped[Business] = relationship(back_populates="memories")
