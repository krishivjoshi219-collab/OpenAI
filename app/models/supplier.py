"""Supplier model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDTimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.product import Product


class Supplier(UUIDTimestampMixin, Base):
    """A supplier available to a business."""

    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("business_id", "email", name="uq_suppliers_business_email"),)

    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(500))

    business: Mapped[Business] = relationship(back_populates="suppliers")
    products: Mapped[list[Product]] = relationship(back_populates="supplier")
