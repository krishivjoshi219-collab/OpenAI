"""Business tenant model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDTimestampMixin

if TYPE_CHECKING:
    from app.models.business_memory import BusinessMemory
    from app.models.customer import Customer
    from app.models.inventory import Inventory
    from app.models.invoice import Invoice
    from app.models.product import Product
    from app.models.reminder import Reminder
    from app.models.settings import Settings
    from app.models.supplier import Supplier


class Business(UUIDTimestampMixin, Base):
    """A company whose operational data is managed by the application."""

    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    customers: Mapped[list[Customer]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    suppliers: Mapped[list[Supplier]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    products: Mapped[list[Product]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    invoices: Mapped[list[Invoice]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    inventory_records: Mapped[list[Inventory]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    memories: Mapped[list[BusinessMemory]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    settings: Mapped[Settings | None] = relationship(
        back_populates="business", cascade="all, delete-orphan", uselist=False
    )
    reminders: Mapped[list[Reminder]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
