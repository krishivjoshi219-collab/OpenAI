"""Provider-neutral notification services and channel adapters."""

from app.notifications.contracts import (
    ApprovalRequest,
    DailySummary,
    InvoiceReminder,
    LowInventoryAlert,
    NotificationTarget,
)
from app.notifications.service import NotificationService
from app.notifications.telegram import TelegramNotificationChannel


def create_notification_service() -> NotificationService:
    """Lazily load runtime configuration and create the Telegram-backed service."""

    from app.notifications.client import create_notification_service as create_service

    return create_service()

__all__ = [
    "ApprovalRequest",
    "DailySummary",
    "InvoiceReminder",
    "LowInventoryAlert",
    "NotificationService",
    "NotificationTarget",
    "TelegramNotificationChannel",
    "create_notification_service",
]
