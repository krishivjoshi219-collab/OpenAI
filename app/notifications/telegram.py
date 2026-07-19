"""Production-grade Telegram Bot API client with retries, formatting, and rich media."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.notifications.contracts import DeliveryReceipt, NotificationMessage

logger = logging.getLogger(__name__)


class ParseMode(StrEnum):
    """Telegram message formatting options."""

    MARKDOWN_V2 = "MarkdownV2"
    HTML = "HTML"
    PLAIN = ""


class TelegramError(Exception):
    """Base exception for Telegram delivery failures."""

    def __init__(self, message: str, *, retry_after: int | None = None, is_rate_limit: bool = False) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.is_rate_limit = is_rate_limit


class TelegramFloodWaitError(TelegramError):
    """Raised when Telegram returns a 429 flood-wait response."""


class TelegramApiError(TelegramError):
    """Raised when Telegram returns a non-OK API response."""


class TelegramTransport(Protocol):
    """Minimal transport seam that makes Telegram delivery independently testable."""

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON and return the decoded Telegram response."""


class UrlLibTelegramTransport:
    """Standard-library HTTP transport for the Telegram Bot API."""

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310 - URL is Telegram-owned.
                body = response.read().decode("utf-8")
        except (HTTPError, URLError) as error:
            raise TelegramError(f"Telegram delivery failed: {error}") from error
        decoded = json.loads(body)
        if not isinstance(decoded, dict):
            raise TelegramError("Telegram returned an invalid response.")
        return decoded


@dataclass(frozen=True)
class InlineButton:
    """One button in an inline keyboard."""

    label: str
    callback_data: str
    style: str = "default"


@dataclass(frozen=True)
class TelegramMessage:
    """Rich Telegram message with optional formatting and interactive elements."""

    text: str
    parse_mode: ParseMode = ParseMode.PLAIN
    disable_web_page_preview: bool = True
    disable_notification: bool = False
    reply_to_message_id: int | None = None
    inline_buttons: list[list[InlineButton]] | None = None
    caption: str | None = None


class TelegramNotificationChannel:
    """Deliver notifications through Telegram's Bot API with retries and formatting."""

    name = "telegram"
    _BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(
        self,
        bot_token: str,
        transport: TelegramTransport | None = None,
        *,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        if not bot_token.strip():
            raise ValueError("A Telegram bot token is required.")
        self._bot_token = bot_token.strip()
        self._transport = transport or UrlLibTelegramTransport()
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    def send(self, message: NotificationMessage, address: str) -> DeliveryReceipt:
        """Send one notification to a Telegram chat ID with retry logic."""

        if not address.strip():
            raise ValueError("A Telegram chat ID is required.")
        chat_id = address.strip()
        telegram_msg = self._build_message(message)
        return self._send_with_retry(telegram_msg, chat_id)

    def send_photo(
        self,
        photo_bytes: bytes,
        caption: str,
        chat_id: str,
        *,
        parse_mode: ParseMode = ParseMode.HTML,
        reply_to_message_id: int | None = None,
    ) -> DeliveryReceipt:
        """Send a photo with caption (used for invoice images)."""

        url = self._url("sendPhoto")
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": parse_mode.value if parse_mode != ParseMode.PLAIN else None,
            "disable_notification": False,
        }
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if parse_mode == ParseMode.PLAIN:
            payload.pop("parse_mode", None)

        fields: dict[str, tuple[str, bytes, str]] = {
            "photo": ("invoice.jpg", photo_bytes, "image/jpeg"),
        }
        return self._multipart_send_with_retry(url, payload, fields, chat_id)

    def send_document(
        self,
        document_bytes: bytes,
        filename: str,
        caption: str,
        chat_id: str,
        *,
        parse_mode: ParseMode = ParseMode.HTML,
        reply_to_message_id: int | None = None,
    ) -> DeliveryReceipt:
        """Send a document (used for PDF invoices)."""

        url = self._url("sendDocument")
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": parse_mode.value if parse_mode != ParseMode.PLAIN else None,
            "disable_notification": False,
        }
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if parse_mode == ParseMode.PLAIN:
            payload.pop("parse_mode", None)

        fields: dict[str, tuple[str, bytes, str]] = {
            "document": (filename, document_bytes, "application/pdf"),
        }
        return self._multipart_send_with_retry(url, payload, fields, chat_id)

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: str,
        *,
        show_alert: bool = False,
    ) -> None:
        """Answer an inline keyboard callback query."""

        url = self._url("answerCallbackQuery")
        payload = {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
        }
        try:
            self._transport.post_json(url, payload)
        except TelegramError as error:
            logger.warning("Failed to answer callback query %s: %s", callback_query_id, error)

    def _build_message(self, message: NotificationMessage) -> TelegramMessage:
        """Convert a notification message into a formatted Telegram message."""

        lines = [f"*{self._escape(message.title)}*", ""]
        body = message.body.replace("\n", "\n")
        lines.append(body)
        return TelegramMessage(
            text="\n".join(lines),
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )

    def _send_with_retry(self, message: TelegramMessage, chat_id: str) -> DeliveryReceipt:
        """Send a JSON message with exponential backoff retry."""

        url = self._url("sendMessage")
        payload = self._text_payload(message, chat_id)
        delay = self._base_delay

        last_error: TelegramError | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._transport.post_json(url, payload)
                return self._handle_response(response, chat_id)
            except TelegramFloodWaitError as error:
                wait = error.retry_after or int(delay)
                logger.warning("Telegram flood wait %ds (attempt %d/%d)", wait, attempt, self._max_retries)
                time.sleep(wait + 0.5)
                last_error = error
            except TelegramError as error:
                if not error.is_rate_limit and attempt < self._max_retries:
                    logger.warning("Telegram send failed (attempt %d/%d): %s", attempt, self._max_retries, error)
                    time.sleep(delay)
                    delay = min(delay * 2, self._max_delay)
                    last_error = error
                elif not error.is_rate_limit:
                    raise
                else:
                    last_error = error

        raise TelegramError(f"Max retries exceeded: {last_error}") from last_error

    def _multipart_send_with_retry(
        self,
        url: str,
        payload: dict[str, Any],
        fields: dict[str, tuple[str, bytes, str]],
        chat_id: str,
    ) -> DeliveryReceipt:
        """Send multipart form data with retry."""

        delay = self._base_delay
        last_error: TelegramError | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._multipart_post(url, payload, fields)
                return self._handle_response(response, chat_id)
            except TelegramFloodWaitError as error:
                wait = error.retry_after or int(delay)
                logger.warning("Telegram flood wait %ds (attempt %d/%d)", wait, attempt, self._max_retries)
                time.sleep(wait + 0.5)
                last_error = error
            except TelegramError as error:
                if attempt < self._max_retries:
                    logger.warning("Telegram multipart send failed (attempt %d/%d): %s", attempt, self._max_retries, error)
                    time.sleep(delay)
                    delay = min(delay * 2, self._max_delay)
                    last_error = error
                else:
                    raise

        raise TelegramError(f"Max retries exceeded: {last_error}") from last_error

    def _multipart_post(
        self,
        url: str,
        payload: dict[str, Any],
        fields: dict[str, tuple[str, bytes, str]],
    ) -> dict[str, Any]:
        """POST multipart form data (for photo/document uploads)."""

        try:
            import httplib2  # type: ignore[import-untyped]
            import uritemplate  # type: ignore[import-untyped]
        except ImportError:
            raise TelegramError("multipart upload requires httplib2 and uritemplate packages") from None

        try:
            import requests
        except ImportError:
            raise TelegramError("multipart upload requires requests package") from None

        files: dict[str, Any] = {}
        for key, (filename, content, mime_type) in fields.items():
            files[key] = (filename, content, mime_type)

        try:
            response = requests.post(url, data=payload, files=files, timeout=30)
            response.raise_for_status()
            result = response.json()
        except Exception as error:
            raise TelegramError(f"Telegram multipart delivery failed: {error}") from error

        if not isinstance(result, dict):
            raise TelegramError("Telegram returned an invalid multipart response.")
        return result

    def _handle_response(self, response: dict[str, Any], chat_id: str) -> DeliveryReceipt:
        """Normalize a successful or failed Telegram API response."""

        if response.get("ok") is not True:
            description = response.get("description", "Telegram rejected the message.")
            error_code = response.get("error_code")
            if error_code == 429:
                parameters = response.get("parameters", {})
                retry_after = parameters.get("retry_after")
                raise TelegramFloodWaitError(
                    f"Telegram rate limited: {description}",
                    retry_after=retry_after,
                    is_rate_limit=True,
                )
            raise TelegramApiError(description, is_rate_limit=False)
        result = response.get("result", {})
        if not isinstance(result, dict):
            raise TelegramError("Telegram response missing result.")
        message_id = result.get("message_id")
        return DeliveryReceipt(
            channel=self.name,
            address=chat_id,
            status="sent",
            provider_message_id=str(message_id) if message_id is not None else None,
        )

    def _text_payload(self, message: TelegramMessage, chat_id: str) -> dict[str, Any]:
        """Build a sendMessage payload."""

        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": message.text,
            "disable_web_page_preview": message.disable_web_page_preview,
            "disable_notification": message.disable_notification,
        }
        if message.parse_mode != ParseMode.PLAIN:
            payload["parse_mode"] = message.parse_mode.value
        if message.reply_to_message_id is not None:
            payload["reply_to_message_id"] = message.reply_to_message_id
        if message.inline_buttons:
            payload["reply_markup"] = {
                "inline_keyboard": [
                    [{"text": btn.label, "callback_data": btn.callback_data} for btn in row]
                    for row in message.inline_buttons
                ],
            }
        return payload

    def _url(self, method: str) -> str:
        return self._BASE_URL.format(token=self._bot_token, method=method)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape text for Telegram MarkdownV2 formatting."""

        return (
            text.replace("\\", "\\\\")
            .replace("_", "\\_")
            .replace("*", "\\*")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("~", "\\~")
            .replace("`", "\\`")
            .replace(">", "\\>")
            .replace("#", "\\#")
            .replace("+", "\\+")
            .replace("-", "\\-")
            .replace("=", "\\=")
            .replace("|", "\\|")
            .replace("{", "\\{")
            .replace("}", "\\}")
            .replace(".", "\\.")
            .replace("!", "\\!")
        )
