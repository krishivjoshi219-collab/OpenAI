"""OpenAI SDK client factory."""

from uuid import UUID

from config.settings import get_settings
from openai import OpenAI

from app.ai.adapters import create_business_tool_registry
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


def create_openai_client() -> OpenAI:
    """Create the configured OpenAI client used by the Responses API service."""

    return OpenAI(api_key=get_settings().openai_api_key)


def create_ai_service() -> AIService:
    """Create the application's configured Responses API service."""

    settings = get_settings()
    return AIService(client=create_openai_client(), model=settings.openai_model)


def create_business_ai_service(engine: BusinessEngine, business_id: UUID) -> AIService:
    """Create an AI service with tools restricted to one business scope."""

    settings = get_settings()
    return AIService(
        client=create_openai_client(),
        model=settings.openai_model,
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
        client=create_openai_client(),
        model=settings.openai_model,
        tool_registry=create_odoo_tool_registry(
            OdooCustomerService(gateway),
            OdooInvoiceService(gateway),
            OdooInventoryService(gateway),
            OdooReminderService(gateway),
        ),
    )
