"""Typed runtime configuration loaded from environment variables."""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_database_url() -> str:
    """Return a database URL with production safety checks.

    In production/hosted environments, require an explicit DATABASE_URL.
    In development/test, allow SQLite fallback (non-persistent on ephemeral hosts).
    """
    app_env = os.getenv("APP_ENV", "development").lower()
    database_url = os.getenv("DATABASE_URL")

    # Production/hosted environments must provide a durable PostgreSQL DATABASE_URL
    if app_env in ("production", "prod", "staging"):
        if not database_url:
            raise ValueError(
                f"DATABASE_URL environment variable is required in {app_env} environment. "
                "SQLite is not suitable for production use due to lack of persistence "
                "on ephemeral/hosted infrastructure."
            )
        if database_url.startswith("sqlite"):
            raise ValueError(
                f"SQLite DATABASE_URL is not allowed in {app_env} environment. "
                "Use a durable PostgreSQL database for production/staging."
            )
        return database_url

    # Development/test: allow SQLite fallback (non-persistent warning implicit)
    return database_url or "sqlite:////tmp/ai_operations_employee.db"


class Settings(BaseSettings):
    """Configuration shared by all application entry points."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = _get_default_database_url()
    # AI provider selection: "openai" | "groq" | "gemini"
    ai_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    odoo_url: str | None = None
    odoo_db: str | None = None
    odoo_database: str | None = None
    odoo_username: str | None = None
    odoo_password: str | None = None
    odoo_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
