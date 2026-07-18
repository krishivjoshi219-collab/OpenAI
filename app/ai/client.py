"""AI provider client factories.

Supports three providers:
  - openai  — native Responses API (default)
  - groq    — Chat Completions via the Groq endpoint
  - gemini  — Chat Completions via Google's OpenAI-compatible endpoint

The active provider is controlled by the ``AI_PROVIDER`` environment variable
(default: ``openai``).  Groq and Gemini use a Chat Completions adapter so that
the rest of the application can use ``AIService`` unchanged.
"""

from uuid import UUID

from config.settings import get_settings
from openai import OpenAI

from app.ai.adapters import create_business_tool_registry
from app.ai.chat_adapter import ChatCompletionsClient
from app.ai.contracts import ResponsesClient
from app.ai.odoo_tools import create_odoo_tool_registry
from app.ai.service import AIService
from app.business.engine import BusinessEngine
from app.business.odoo import (
    OdooCustomerService,
    OdooInventoryService,
    OdooInvoiceService,
    OdooJsonRpcClient,
    OdooReminderService,
)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def create_openai_client() -> OpenAI:
    """Create the configured OpenAI client used by the Responses API service."""

    return OpenAI(api_key=get_settings().openai_api_key)


def create_groq_client() -> ChatCompletionsClient:
    """Create a Groq Chat Completions client wrapped in the ResponsesClient adapter."""

    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required to use the Groq provider.")
    raw = OpenAI(api_key=settings.groq_api_key, base_url=_GROQ_BASE_URL)
    return ChatCompletionsClient(raw)


def create_gemini_client() -> ChatCompletionsClient:
    """Create a Gemini Chat Completions client wrapped in the ResponsesClient adapter."""

    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required to use the Gemini provider.")
    raw = OpenAI(api_key=settings.gemini_api_key, base_url=_GEMINI_BASE_URL)
    return ChatCompletionsClient(raw)


def create_provider_client() -> ResponsesClient:
    """Return the configured AI provider client based on ``AI_PROVIDER``."""

    provider = get_settings().ai_provider.lower()
    if provider == "groq":
        return create_groq_client()
    if provider == "gemini":
        return create_gemini_client()
    return create_openai_client()


def create_provider_model() -> str:
    """Return the model name for the active provider."""

    settings = get_settings()
    provider = settings.ai_provider.lower()
    if provider == "groq":
        return settings.groq_model
    if provider == "gemini":
        return settings.gemini_model
    return settings.openai_model


def create_ai_service() -> AIService:
    """Create the application's AI service using the configured provider."""

    return AIService(client=create_provider_client(), model=create_provider_model())


def create_business_ai_service(engine: BusinessEngine, business_id: UUID) -> AIService:
    """Create an AI service with tools restricted to one business scope."""

    return AIService(
        client=create_provider_client(),
        model=create_provider_model(),
        tool_registry=create_business_tool_registry(engine, business_id),
    )


def create_odoo_ai_service() -> AIService:
    """Create an AI service exposing only the configured Odoo tool allowlist."""

    settings = get_settings()
    if not all(
        [settings.odoo_url, settings.odoo_database, settings.odoo_username, settings.odoo_api_key]
    ):
        raise ValueError("ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, and ODOO_API_KEY are required.")
    gateway = OdooJsonRpcClient(
        settings.odoo_url or "",
        settings.odoo_database or "",
        settings.odoo_username or "",
        settings.odoo_api_key or "",
    )
    return AIService(
        client=create_provider_client(),
        model=create_provider_model(),
        tool_registry=create_odoo_tool_registry(
            OdooCustomerService(gateway),
            OdooInvoiceService(gateway),
            OdooInventoryService(gateway),
            OdooReminderService(gateway),
        ),
    )
