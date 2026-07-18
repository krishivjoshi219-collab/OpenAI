"""Business-level application settings model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDTimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business


class Settings(UUIDTimestampMixin, Base):
    """One extensible settings record for each business."""

    __tablename__ = "settings"

    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    values: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    business: Mapped[Business] = relationship(back_populates="settings")
