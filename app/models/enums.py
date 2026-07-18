"""Enumerations persisted by the operations data model."""

from enum import Enum


class InvoiceStatus(str, Enum):
    """Lifecycle states for customer invoices."""

    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"

