"""Telegram Bot API implementation of the notification-channel contract."""

from __future__ import annotations

import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.notifications.contracts import DeliveryReceipt, NotificationMessage


class TelegramTransport(Protocol):
    """Minimal transport seam that makes Telegram delivery independently testable."""

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON and return the decoded Telegram response."""


class UrlLibTelegramTransport:
    """Small standard-library HTTP transport for the Telegram Bot API."""

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - URL is Telegram-owned.
                body = response.read().decode("utf-8")
        except (HTTPError, URLError) as error:
            raise RuntimeError(f"Telegram delivery failed: {error}") from error
        decoded = json.loads(body)
        if not isinstance(decoded, dict):
            raise RuntimeError("Telegram returned an invalid response.")
        return decoded


class TelegramNotificationChannel:
    """Deliver plain-text notifications through Telegram's ``sendMessage`` endpoint."""

    name = "telegram"

    def __init__(self, bot_token: str, transport: TelegramTransport | None = None) -> None:
        if not bot_token.strip():
            raise ValueError("A Telegram bot token is required.")
        self._bot_token = bot_token
        self._transport = transport or UrlLibTelegramTransport()

    def send(self, message: NotificationMessage, address: str) -> DeliveryReceipt:
        """Send one notification to a Telegram chat ID."""

        if not address.strip():
            raise ValueError("A Telegram chat ID is required.")
        response = self._transport.post_json(
            f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
            {"chat_id": address, "text": f"{message.title}\n\n{message.body}"},
        )
        if response.get("ok") is not True:
            raise RuntimeError(str(response.get("description", "Telegram rejected the message.")))
        result = response.get("result", {})
        message_id = result.get("message_id") if isinstance(result, dict) else None
        return DeliveryReceipt(
            channel=self.name,
            address=address,
            status="sent",
            provider_message_id=str(message_id) if message_id is not None else None,
        )
