"""Provider-neutral notification contracts and payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any, Protocol


class NotificationKind(StrEnum):
    """Business events the application can notify about."""

    DAILY_SUMMARY = "daily_summary"
    INVOICE_REMINDER = "invoice_reminder"
    LOW_INVENTORY = "low_inventory"
    APPROVAL_REQUEST = "approval_request"


@dataclass(frozen=True)
class NotificationMessage:
    """A provider-independent, plain-text business notification."""

    kind: NotificationKind
    title: str
    body: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class NotificationTarget:
    """A destination address for a configured delivery channel."""

    channel: str
    address: str


@dataclass(frozen=True)
class DeliveryReceipt:
    """The normalized outcome of one attempted notification delivery."""

    channel: str
    address: str
    status: str
    provider_message_id: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class NotificationDispatch:
    """A message and the outcomes for every selected target."""

    message: NotificationMessage
    deliveries: tuple[DeliveryReceipt, ...]


class NotificationChannel(Protocol):
    """A replaceable outbound channel such as Telegram, SMS, or email."""

    name: str

    def send(self, message: NotificationMessage, address: str) -> DeliveryReceipt:
        """Deliver one message to one provider-specific destination."""


@dataclass(frozen=True)
class DailySummary:
    """Data displayed in a daily operational summary."""

    business_name: str
    summary_date: date
    metrics: dict[str, str | int | float]


@dataclass(frozen=True)
class InvoiceReminder:
    """Data required for an invoice payment reminder."""

    invoice_number: str
    customer_name: str
    amount: str
    due_date: date
    currency_code: str


@dataclass(frozen=True)
class LowInventoryAlert:
    """Data required for a stock replenishment alert."""

    product_name: str
    sku: str
    quantity_on_hand: str
    reorder_level: str


@dataclass(frozen=True)
class ApprovalRequest:
    """Data required to ask an operator for an explicit approval."""

    title: str
    details: str
    requested_by: str = "AI Operations Employee"
