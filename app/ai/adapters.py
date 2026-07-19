"""Adapters that expose scoped :class:`BusinessEngine` operations as AI tools."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID

from app.ai.contracts import ToolDefinition
from app.ai.tools import ToolRegistry
from app.business.commands import (
    CreateCustomer,
    CreateInvoice,
    CreateInvoiceLine,
    CreateProduct,
    CreateReminder,
    UpdateInventory,
)
from app.business.engine import BusinessEngine
from app.models import Customer, Inventory, Invoice, Product, Reminder
from app.models.enums import InvoiceStatus


def _schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    """Build the strict object schema required by Responses function tools."""

    return {
        "type": "object",
        "properties": {**properties, "reason": {"type": "string", "description": "Why this action is needed."}},
        "required": required,
        "additionalProperties": False,
    }


class BusinessToolAdapter:
    """Bind model-visible tools to one business-scoped business engine instance."""

    def __init__(self, engine: BusinessEngine, business_id: UUID) -> None:
        self._engine = engine
        self._business_id = business_id

    def register_tools(self, registry: ToolRegistry) -> None:
        """Register the complete supported business tool set on ``registry``."""

        for definition, handler in self._tools():
            registry.register(definition, handler)

    def _tools(self) -> list[tuple[ToolDefinition, Callable[[dict[str, Any]], dict[str, Any]]]]:
        nullable_string = {"type": ["string", "null"]}
        nullable_number = {"type": ["number", "null"]}
        nullable_uuid = {"type": ["string", "null"], "format": "uuid"}
        return [
            (
                ToolDefinition("create_customer", "Create a customer record.", _schema({"name": {"type": "string"}, "email": nullable_string, "phone": nullable_string, "billing_address": nullable_string}, ["name", "email", "phone", "billing_address"])),
                self.create_customer,
            ),
            (
                ToolDefinition("search_customers", "Search customers by name or email before using a customer ID.", _schema({"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, ["query", "limit"])),
                self.search_customers,
            ),
            (
                ToolDefinition("create_product", "Create a product in the catalogue.", _schema({"name": {"type": "string"}, "sku": {"type": "string"}, "unit_price": {"type": "number"}, "cost_price": nullable_number, "description": nullable_string, "supplier_id": nullable_uuid}, ["name", "sku", "unit_price", "cost_price", "description", "supplier_id"])),
                self.create_product,
            ),
            (
                ToolDefinition("search_products", "Search products by name or SKU before using a product ID.", _schema({"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, ["query", "limit"])),
                self.search_products,
            ),
            (
                ToolDefinition("update_inventory", "Set the current inventory position for a product.", _schema({"product_id": {"type": "string", "format": "uuid"}, "quantity_on_hand": {"type": "number"}, "reorder_level": nullable_number}, ["product_id", "quantity_on_hand", "reorder_level"])),
                self.update_inventory,
            ),
            (
                ToolDefinition("create_reminder", "Create an operational reminder.", _schema({"title": {"type": "string"}, "details": nullable_string, "due_at": {"type": ["string", "null"], "format": "date-time"}}, ["title", "details", "due_at"])),
                self.create_reminder,
            ),
            (
                ToolDefinition("create_invoice", "Create a draft or specified-status invoice with one or more lines.", _schema({"customer_id": {"type": "string", "format": "uuid"}, "invoice_number": {"type": "string"}, "lines": {"type": "array", "minItems": 1, "items": {"type": "object", "properties": {"quantity": {"type": "number"}, "product_id": nullable_uuid, "description": nullable_string, "unit_price": nullable_number, "tax_rate": {"type": "number"}}, "required": ["quantity", "product_id", "description", "unit_price", "tax_rate"], "additionalProperties": False}}, "issued_on": {"type": ["string", "null"], "format": "date"}, "due_on": {"type": ["string", "null"], "format": "date"}, "currency_code": nullable_string, "status": {"type": "string", "enum": [item.value for item in InvoiceStatus]}, "notes": nullable_string}, ["customer_id", "invoice_number", "lines", "issued_on", "due_on", "currency_code", "status", "notes"])),
                self.create_invoice,
            ),
        ]

    def create_customer(self, arguments: dict[str, Any]) -> dict[str, Any]:
        customer = self._engine.create_customer(self._business_id, CreateCustomer(**self._without_reason(arguments)))
        return self._completed("create_customer", customer, self._customer)

    def search_customers(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        records = self._engine.search_customers(self._business_id, values["query"], limit=values["limit"])
        return {"status": "completed", "action": "search_customers", "data": [self._customer(item) for item in records]}

    def create_product(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        values["unit_price"] = Decimal(str(values["unit_price"]))
        values["cost_price"] = self._decimal(values["cost_price"])
        values["supplier_id"] = self._uuid(values["supplier_id"])
        product = self._engine.create_product(self._business_id, CreateProduct(**values))
        return self._completed("create_product", product, self._product)

    def search_products(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        records = self._engine.search_products(self._business_id, values["query"], limit=values["limit"])
        return {"status": "completed", "action": "search_products", "data": [self._product(item) for item in records]}

    def update_inventory(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        values["product_id"] = UUID(values["product_id"])
        values["quantity_on_hand"] = Decimal(str(values["quantity_on_hand"]))
        values["reorder_level"] = self._decimal(values["reorder_level"])
        inventory = self._engine.update_inventory(self._business_id, UpdateInventory(**values))
        return self._completed("update_inventory", inventory, self._inventory)

    def create_reminder(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        values["due_at"] = datetime.fromisoformat(values["due_at"]) if values["due_at"] else None
        reminder = self._engine.create_reminder(self._business_id, CreateReminder(**values))
        return self._completed("create_reminder", reminder, self._reminder)

    def create_invoice(self, arguments: dict[str, Any]) -> dict[str, Any]:
        values = self._without_reason(arguments)
        values["customer_id"] = UUID(values["customer_id"])
        values["issued_on"] = date.fromisoformat(values["issued_on"]) if values["issued_on"] else None
        values["due_on"] = date.fromisoformat(values["due_on"]) if values["due_on"] else None
        values["status"] = InvoiceStatus(values["status"])
        values["lines"] = tuple(self._invoice_line(line) for line in values["lines"])
        invoice = self._engine.create_invoice(self._business_id, CreateInvoice(**values))
        return self._completed("create_invoice", invoice, self._invoice)

    @staticmethod
    def _without_reason(arguments: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in arguments.items() if key != "reason"}

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        return Decimal(str(value)) if value is not None else None

    @staticmethod
    def _uuid(value: str | None) -> UUID | None:
        return UUID(value) if value else None

    def _invoice_line(self, values: dict[str, Any]) -> CreateInvoiceLine:
        return CreateInvoiceLine(quantity=Decimal(str(values["quantity"])), product_id=self._uuid(values["product_id"]), description=values["description"], unit_price=self._decimal(values["unit_price"]), tax_rate=Decimal(str(values["tax_rate"])))

    @staticmethod
    def _completed(action: str, record: Any, serializer: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
        return {"status": "completed", "action": action, "data": serializer(record)}

    @staticmethod
    def _customer(record: Customer) -> dict[str, Any]:
        return {"id": str(record.id), "name": record.name, "email": record.email, "phone": record.phone}

    @staticmethod
    def _product(record: Product) -> dict[str, Any]:
        return {"id": str(record.id), "name": record.name, "sku": record.sku, "unit_price": str(record.unit_price)}

    @staticmethod
    def _inventory(record: Inventory) -> dict[str, Any]:
        return {"id": str(record.id), "product_id": str(record.product_id), "quantity_on_hand": str(record.quantity_on_hand), "reorder_level": str(record.reorder_level)}

    @staticmethod
    def _reminder(record: Reminder) -> dict[str, Any]:
        return {"id": str(record.id), "title": record.title, "due_at": record.due_at.isoformat() if record.due_at else None, "is_completed": record.is_completed}

    @staticmethod
    def _invoice(record: Invoice) -> dict[str, Any]:
        return {"id": str(record.id), "invoice_number": record.invoice_number, "customer_id": str(record.customer_id), "status": record.status.value, "currency_code": record.currency_code, "subtotal": str(record.subtotal), "tax_total": str(record.tax_total), "total": str(record.total)}


def create_business_tool_registry(engine: BusinessEngine, business_id: UUID) -> ToolRegistry:
    """Return a registry exposing only operations for the supplied business."""

    registry = ToolRegistry()
    BusinessToolAdapter(engine, business_id).register_tools(registry)
    return registry
