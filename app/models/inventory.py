"""Inventory balance model."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDTimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.product import Product


class Inventory(UUIDTimestampMixin, Base):
    """Current stock position for one product within one business."""

    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("business_id", "product_id", name="uq_inventory_business_product"),
    )

    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    quantity_on_hand: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0")
    )
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0")
    )

    business: Mapped[Business] = relationship(back_populates="inventory_records")
    product: Mapped[Product] = relationship(back_populates="inventory")
