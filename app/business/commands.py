"""Typed inputs accepted by the business engine's Python command surface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.models.enums import InvoiceStatus


@dataclass(frozen=True)
class CreateCustomer:
    """Input for creating one customer."""

    name: str
    email: str | None = None
    phone: str | None = None
    billing_address: str | None = None


@dataclass(frozen=True)
class CreateProduct:
    """Input for creating one product."""

    name: str
    sku: str
    unit_price: Decimal
    cost_price: Decimal | None = None
    description: str | None = None
    supplier_id: UUID | None = None


@dataclass(frozen=True)
class CreateInvoiceLine:
    """Input for one invoice line, with optional product price lookup."""

    quantity: Decimal
    product_id: UUID | None = None
    description: str | None = None
    unit_price: Decimal | None = None
    tax_rate: Decimal = Decimal("0")


@dataclass(frozen=True)
class CreateInvoice:
    """Input for a complete invoice and its lines."""

    customer_id: UUID
    invoice_number: str
    lines: tuple[CreateInvoiceLine, ...]
    issued_on: date | None = None
    due_on: date | None = None
    currency_code: str | None = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    notes: str | None = None


@dataclass(frozen=True)
class UpdateInventory:
    """Input for setting a product's current inventory position."""

    product_id: UUID
    quantity_on_hand: Decimal
    reorder_level: Decimal | None = None


@dataclass(frozen=True)
class CreateReminder:
    """Input for a business-scoped operational reminder."""

    title: str
    details: str | None = None
    due_at: datetime | None = None
