"""Typed runtime configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration shared by all application entry points."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:////tmp/ai_operations_employee.db"
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
