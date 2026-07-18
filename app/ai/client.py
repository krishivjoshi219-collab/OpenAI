"""OpenAI SDK client factory."""

from openai import OpenAI

from app.ai.service import AIService
from config.settings import get_settings


def create_openai_client() -> OpenAI:
    """Create the configured OpenAI client used by the Responses API service."""

    return OpenAI(api_key=get_settings().openai_api_key)


def create_ai_service() -> AIService:
    """Create the application's configured Responses API service."""

    settings = get_settings()
    return AIService(client=create_openai_client(), model=settings.openai_model)
