"""Tests for provider-neutral notification routing and Telegram delivery."""

from datetime import date
from typing import Any

from app.notifications.contracts import (
    ApprovalRequest,
    DailySummary,
    DeliveryReceipt,
    InvoiceReminder,
    LowInventoryAlert,
    NotificationMessage,
    NotificationTarget,
    NotificationKind,
)
from app.notifications.service import NotificationService
from app.notifications.telegram import TelegramNotificationChannel


class _FakeChannel:
    name = "fake"

    def __init__(self) -> None:
        self.sent: list[tuple[NotificationMessage, str]] = []

    def send(self, message: NotificationMessage, address: str) -> DeliveryReceipt:
        self.sent.append((message, address))
        return DeliveryReceipt(channel=self.name, address=address, status="sent", provider_message_id="1")


def test_notification_service_formats_and_routes_all_business_events() -> None:
    """Each requested event becomes a structured message sent through the same seam."""

    channel = _FakeChannel()
    service = NotificationService([channel], [NotificationTarget("fake", "ops")])

    summary = service.send_daily_summary(
        DailySummary("Acme", date(2026, 7, 18), {"Invoices paid": 3})
    )
    invoice = service.send_invoice_reminder(
        InvoiceReminder("INV-7", "Ada", "100.00", date(2026, 7, 20), "USD")
    )
    inventory = service.send_low_inventory_alert(LowInventoryAlert("Widget", "W-1", "2", "5"))
    approval = service.send_approval_request(ApprovalRequest("Send quote", "Quote is ready."))

    assert [item[0].kind.value for item in channel.sent] == [
        "daily_summary",
        "invoice_reminder",
        "low_inventory",
        "approval_request",
    ]
    assert summary.deliveries[0].status == "sent"
    assert "INV-7" in invoice.message.title
    assert "On hand: 2" in inventory.message.body
    assert "Requested by" in approval.message.body


def test_notification_service_records_unconfigured_channel_failure() -> None:
    """A bad route produces a structured failure instead of raising for callers."""

    service = NotificationService([], [NotificationTarget("slack", "channel-1")])
    dispatch = service.send_approval_request(ApprovalRequest("Confirm", "Please approve."))

    assert dispatch.deliveries[0].status == "failed"
    assert dispatch.deliveries[0].error == "Notification channel is not configured."


class _FakeTelegramTransport:
    def __init__(self) -> None:
        self.url = ""
        self.payload: dict[str, Any] = {}

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.url = url
        self.payload = payload
        return {"ok": True, "result": {"message_id": 42}}


def test_telegram_channel_calls_bot_api_and_normalizes_receipt() -> None:
    """Telegram-specific HTTP details stay inside the Telegram adapter."""

    transport = _FakeTelegramTransport()
    channel = TelegramNotificationChannel("secret-token", transport)
    receipt = channel.send(
        NotificationMessage(
            kind=NotificationKind.DAILY_SUMMARY,
            title="Summary",
            body="All good",
            metadata={},
        ),
        "12345",
    )

    assert transport.url.endswith("botsecret-token/sendMessage")
    assert transport.payload["chat_id"] == "12345"
    assert transport.payload["text"] == "*Summary*\n\nAll good"
    assert transport.payload["parse_mode"] == "MarkdownV2"
    assert transport.payload["disable_web_page_preview"] is True
    assert receipt.provider_message_id == "42"
