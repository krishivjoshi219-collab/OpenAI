"""Runtime factory for configured notification services."""

from app.notifications.contracts import NotificationTarget
from app.notifications.service import NotificationService
from app.notifications.telegram import TelegramNotificationChannel
from config.settings import get_settings


def create_notification_service() -> NotificationService:
    """Create the application's Telegram-backed notification service."""

    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured.")
    return NotificationService(
        channels=[TelegramNotificationChannel(settings.telegram_bot_token)],
        default_targets=[NotificationTarget(channel="telegram", address=settings.telegram_chat_id)],
    )
