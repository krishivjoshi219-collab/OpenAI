"""Tests for the Odoo service layer and its OpenAI function-tool boundary."""

from datetime import date
from typing import Any

from app.ai.odoo_tools import create_odoo_tool_registry
from app.business.odoo import (
    OdooCreateCustomer,
    OdooCreateInvoice,
    OdooCustomerService,
    OdooInventoryService,
    OdooInventoryUpdate,
    OdooInvoiceLine,
    OdooInvoiceService,
    OdooJsonRpcClient,
    OdooReminder,
    OdooReminderService,
)


class _FakeGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list[Any], dict[str, Any]]] = []

    def execute(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        self.calls.append((model, method, args, kwargs))
        outcomes: dict[tuple[str, str], Any] = {
            ("res.partner", "create"): 21,
            ("res.partner", "search_read"): [{"id": 21, "name": "Ada"}],
            ("account.move", "create"): 31,
            ("account.move", "action_send_and_print"): {"type": "ir.actions.act_window"},
            ("stock.quant", "search"): [],
            ("stock.quant", "create"): 41,
            ("stock.quant", "action_apply_inventory"): True,
            ("ir.model", "search"): [99],
            ("mail.activity", "create"): 51,
        }
        return outcomes[(model, method)]


def test_odoo_services_map_business_operations_to_expected_models() -> None:
    """Service classes retain Odoo model details behind focused operations."""

    gateway = _FakeGateway()
    customers = OdooCustomerService(gateway)
    invoices = OdooInvoiceService(gateway)
    inventory = OdooInventoryService(gateway)
    reminders = OdooReminderService(gateway)

    assert customers.create(OdooCreateCustomer("Ada"))["id"] == 21
    assert customers.search("Ada")[0]["name"] == "Ada"
    assert (
        invoices.create(
            OdooCreateInvoice(21, (OdooInvoiceLine("Consulting", 2, 100),), date(2026, 7, 18))
        )["id"]
        == 31
    )
    assert invoices.send(31)["status"] == "requested"
    assert inventory.update(OdooInventoryUpdate(7, 8, 10))["id"] == 41
    assert reminders.create(OdooReminder("res.partner", 21, 1, "Call Ada"))["id"] == 51
    assert ("stock.quant", "action_apply_inventory") in [
        (model, method) for model, method, _, _ in gateway.calls
    ]


def test_odoo_tools_expose_every_supported_service_action() -> None:
    """OpenAI receives an explicit tool for each requested Odoo operation."""

    gateway = _FakeGateway()
    registry = create_odoo_tool_registry(
        OdooCustomerService(gateway),
        OdooInvoiceService(gateway),
        OdooInventoryService(gateway),
        OdooReminderService(gateway),
    )

    names = {definition.name for definition in registry.definitions_for()}

    assert names == {
        "odoo_create_customer",
        "odoo_search_customers",
        "odoo_create_invoice",
        "odoo_update_inventory",
        "odoo_send_invoice",
        "odoo_create_reminder",
    }


class _FakeTransport:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        if payload["params"]["service"] == "common":
            return {"result": 7}
        return {"result": 123}


def test_json_rpc_client_authenticates_once_then_executes() -> None:
    """The RPC client authenticates before its first Odoo object call only."""

    transport = _FakeTransport()
    client = OdooJsonRpcClient("https://odoo.example", "db", "user", "key", transport)

    assert client.execute("res.partner", "create", [{"name": "Ada"}], {}) == 123
    assert client.execute("res.partner", "create", [{"name": "Grace"}], {}) == 123
    assert [payload["params"]["service"] for payload in transport.payloads] == [
        "common",
        "object",
        "object",
    ]
