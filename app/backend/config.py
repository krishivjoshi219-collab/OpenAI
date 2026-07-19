"""Configuration validation and startup checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SettingsValidationError(Exception):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a configuration validation check."""

    field: str
    is_valid: bool
    message: str


def validate_settings(settings: Any) -> list[ValidationResult]:
    """Validate that all required settings are present and well-formed."""

    results: list[ValidationResult] = []

    if not getattr(settings, "database_url", None):
        results.append(ValidationResult("database_url", False, "DATABASE_URL is required."))
    else:
        results.append(ValidationResult("database_url", True, "OK"))

    provider = getattr(settings, "ai_provider", "openai").lower()
    results.append(ValidationResult("ai_provider", True, f"Provider: {provider}"))

    if provider == "openai":
        if not getattr(settings, "openai_api_key", None):
            results.append(ValidationResult("openai_api_key", False, "OPENAI_API_KEY is required for OpenAI provider."))
        else:
            results.append(ValidationResult("openai_api_key", True, "OK"))
    elif provider == "groq":
        if not getattr(settings, "groq_api_key", None):
            results.append(ValidationResult("groq_api_key", False, "GROQ_API_KEY is required for Groq provider."))
        else:
            results.append(ValidationResult("groq_api_key", True, "OK"))
    elif provider == "gemini":
        if not getattr(settings, "gemini_api_key", None):
            results.append(ValidationResult("gemini_api_key", False, "GEMINI_API_KEY is required for Gemini provider."))
        else:
            results.append(ValidationResult("gemini_api_key", True, "OK"))
    else:
        results.append(ValidationResult("ai_provider", False, f"Unknown AI provider: {provider}"))

    telegram_token = getattr(settings, "telegram_bot_token", None)
    telegram_chat = getattr(settings, "telegram_chat_id", None)
    if telegram_token and not telegram_chat:
        results.append(ValidationResult("telegram_chat_id", False, "TELEGRAM_CHAT_ID required when TELEGRAM_BOT_TOKEN is set."))
    elif telegram_chat and not telegram_token:
        results.append(ValidationResult("telegram_bot_token", False, "TELEGRAM_BOT_TOKEN required when TELEGRAM_CHAT_ID is set."))
    elif telegram_token and telegram_chat:
        results.append(ValidationResult("telegram", True, "OK"))
    else:
        results.append(ValidationResult("telegram", True, "Not configured (optional)."))

    odoo_url = getattr(settings, "odoo_url", None)
    if odoo_url:
        required_odoo = ["odoo_database", "odoo_username", "odoo_api_key"]
        missing = [field for field in required_odoo if not getattr(settings, field, None)]
        if missing:
            results.append(ValidationResult("odoo", False, f"Odoo configured but missing: {', '.join(missing)}"))
        else:
            results.append(ValidationResult("odoo", True, "OK"))
    else:
        results.append(ValidationResult("odoo", True, "Not configured (optional)."))

    failures = [r for r in results if not r.is_valid]
    if failures:
        messages = "; ".join(f"{r.field}: {r.message}" for r in failures)
        raise SettingsValidationError(f"Configuration validation failed: {messages}")

    return results
