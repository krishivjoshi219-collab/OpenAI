"""Customer model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDTimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.invoice import Invoice


class Customer(UUIDTimestampMixin, Base):
    """A customer belonging to one business."""

    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("business_id", "email", name="uq_customers_business_email"),)

    business_id: Mapped[UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    billing_address: Mapped[str | None] = mapped_column(String(500))

    business: Mapped[Business] = relationship(back_populates="customers")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="customer")
