"""OpenAI function tools backed by the Odoo business service classes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from app.ai.contracts import AgentProfile, ToolDefinition
from app.ai.tools import ToolRegistry
from app.business.odoo import (
    OdooCreateCustomer,
    OdooCreateInvoice,
    OdooCustomerService,
    OdooInventoryService,
    OdooInventoryUpdate,
    OdooInvoiceLine,
    OdooInvoiceService,
    OdooReminder,
    OdooReminderService,
)

ODOO_AGENT = AgentProfile(
    name="odoo_operations",
    prompt_name="business_command",
    tool_names=frozenset(
        {
            "odoo_create_customer",
            "odoo_search_customers",
            "odoo_create_invoice",
            "odoo_update_inventory",
            "odoo_send_invoice",
            "odoo_create_reminder",
        }
    ),
)


def _schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            **properties,
            "reason": {"type": "string", "description": "Why this Odoo action is needed."},
        },
        "required": [*required, "reason"],
        "additionalProperties": False,
    }


class OdooToolAdapter:
    """Expose a fixed allowlist of Odoo service operations to an OpenAI agent."""

    def __init__(
        self,
        customers: OdooCustomerService,
        invoices: OdooInvoiceService,
        inventory: OdooInventoryService,
        reminders: OdooReminderService,
    ) -> None:
        self._customers = customers
        self._invoices = invoices
        self._inventory = inventory
        self._reminders = reminders

    def register_tools(self, registry: ToolRegistry) -> None:
        """Register every supported Odoo business action."""

        for definition, handler in self._tools():
            registry.register(definition, handler)

    def _tools(self) -> list[tuple[ToolDefinition, Callable[[dict[str, Any]], dict[str, Any]]]]:
        nullable_string = {"type": ["string", "null"]}
        nullable_integer = {"type": ["integer", "null"]}
        return [
            (
                ToolDefinition(
                    "odoo_create_customer",
                    "Create an Odoo customer partner.",
                    _schema(
                        {
                            "name": {"type": "string"},
                            "email": nullable_string,
                            "phone": nullable_string,
                            "street": nullable_string,
                        },
                        ["name", "email", "phone", "street"],
                    ),
                ),
                self.create_customer,
            ),
            (
                ToolDefinition(
                    "odoo_search_customers",
                    "Search Odoo customers by name or email before using a partner ID.",
                    _schema(
                        {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                        },
                        ["query", "limit"],
                    ),
                ),
                self.search_customers,
            ),
            (
                ToolDefinition(
                    "odoo_create_invoice",
                    "Create a draft Odoo customer invoice. Search customers before choosing "
                    "partner_id.",
                    _schema(
                        {
                            "partner_id": {"type": "integer"},
                            "lines": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "quantity": {"type": "number", "exclusiveMinimum": 0},
                                        "price_unit": {"type": "number", "minimum": 0},
                                        "product_id": nullable_integer,
                                    },
                                    "required": ["name", "quantity", "price_unit", "product_id"],
                                    "additionalProperties": False,
                                },
                            },
                            "invoice_date": {"type": ["string", "null"], "format": "date"},
                            "invoice_date_due": {"type": ["string", "null"], "format": "date"},
                            "narration": nullable_string,
                        },
                        ["partner_id", "lines", "invoice_date", "invoice_date_due", "narration"],
                    ),
                ),
                self.create_invoice,
            ),
            (
                ToolDefinition(
                    "odoo_update_inventory",
                    "Apply an Odoo inventory count for a product at a specific stock location.",
                    _schema(
                        {
                            "product_id": {"type": "integer"},
                            "location_id": {"type": "integer"},
                            "quantity": {"type": "number", "minimum": 0},
                        },
                        ["product_id", "location_id", "quantity"],
                    ),
                ),
                self.update_inventory,
            ),
            (
                ToolDefinition(
                    "odoo_send_invoice",
                    "Request Odoo's configured send-and-print workflow for an existing invoice.",
                    _schema({"invoice_id": {"type": "integer"}}, ["invoice_id"]),
                ),
                self.send_invoice,
            ),
            (
                ToolDefinition(
                    "odoo_create_reminder",
                    "Create an Odoo scheduled activity on an existing record.",
                    _schema(
                        {
                            "res_model": {"type": "string"},
                            "res_id": {"type": "integer"},
                            "activity_type_id": {"type": "integer"},
                            "summary": {"type": "string"},
                            "note": nullable_string,
                            "date_deadline": {"type": ["string", "null"], "format": "date"},
                            "user_id": nullable_integer,
                        },
                        [
                            "res_model",
                            "res_id",
                            "activity_type_id",
                            "summary",
                            "note",
                            "date_deadline",
                            "user_id",
                        ],
                    ),
                ),
                self.create_reminder,
            ),
        ]

    def create_customer(self, arguments: dict[str, Any]) -> dict[str, Any]:
        command = OdooCreateCustomer(**self._without_reason(arguments))
        return self._completed("odoo_create_customer", self._customers.create(command))

    def search_customers(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        return self._completed(
            "odoo_search_customers", self._customers.search(values["query"], values["limit"])
        )

    def create_invoice(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        values["lines"] = tuple(OdooInvoiceLine(**line) for line in values["lines"])
        values["invoice_date"] = self._date(values["invoice_date"])
        values["invoice_date_due"] = self._date(values["invoice_date_due"])
        return self._completed(
            "odoo_create_invoice", self._invoices.create(OdooCreateInvoice(**values))
        )

    def update_inventory(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._completed(
            "odoo_update_inventory",
            self._inventory.update(OdooInventoryUpdate(**self._without_reason(arguments))),
        )

    def send_invoice(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        return self._completed("odoo_send_invoice", self._invoices.send(values["invoice_id"]))

    def create_reminder(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        values["date_deadline"] = self._date(values["date_deadline"])
        return self._completed(
            "odoo_create_reminder", self._reminders.create(OdooReminder(**values))
        )

    @staticmethod
    def _without_reason(arguments: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in arguments.items() if key != "reason"}

    @staticmethod
    def _date(value: str | None) -> date | None:
        return date.fromisoformat(value) if value else None

    @staticmethod
    def _completed(action: str, data: Any) -> dict[str, Any]:
        return {"status": "completed", "action": action, "data": data}


def create_odoo_tool_registry(
    customers: OdooCustomerService,
    invoices: OdooInvoiceService,
    inventory: OdooInventoryService,
    reminders: OdooReminderService,
) -> ToolRegistry:
    """Create a registry containing exactly the Odoo operation tool allowlist."""

    registry = ToolRegistry()
    OdooToolAdapter(customers, invoices, inventory, reminders).register_tools(registry)
    return registry
