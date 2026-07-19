"""Enumerations persisted by the operations data model."""

from enum import StrEnum


class InvoiceStatus(StrEnum):
    """Lifecycle states for customer invoices."""

    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"

