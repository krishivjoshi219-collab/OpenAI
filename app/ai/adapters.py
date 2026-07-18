from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from app.business.commands import (
    CreateCustomer,
    CreateInvoice,
    CreateInvoiceLine,
    CreateProduct,
    CreateReminder,
    UpdateInventory,
)
from app.business.engine import BusinessEngine
from app.database.session import session_scope
from app.models import Business

class AIAdapter:
    """Translate ToolCall objects into deterministic BusinessEngine commands."""

    def __init__(self, business_id: UUID) -> None:
        self._business_id = business_id

    def invoke(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a business command using a valid database transaction session context."""

        try:
            with session_scope() as session:
                engine = BusinessEngine(session)
                command = self._parse_tool_call(tool_call)
                result = self._invoke_command(engine, command)
                return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    def _parse_tool_call(self, tool_call: Dict[str, Any]) -> Any:
        """Parse the incoming ToolCall object into a Pydantic DTO command."""

        name = tool_call["name"]
        arguments = tool_call["arguments"]

        if name == "create_customer":
            return CreateCustomer(**arguments)
        elif name == "create_invoice":
            lines = [CreateInvoiceLine(**line) for line in arguments["lines"]]
            return CreateInvoice(**{**arguments, "lines": lines})
        elif name == "create_product":
            return CreateProduct(**arguments)
        elif name == "update_inventory":
            return UpdateInventory(**arguments)
        elif name == "create_reminder":
            return CreateReminder(**arguments)
        else:
            raise ValueError("Unknown tool name")

    def _invoke_command(self, engine: BusinessEngine, command: Any) -> Any:
        """Invoke the corresponding method on the BusinessEngine."""

        if isinstance(command, CreateCustomer):
            return engine.create_customer(self._business_id, command)
        elif isinstance(command, CreateInvoice):
            return engine.create_invoice(self._business_id, command)
        elif isinstance(command, CreateProduct):
            return engine.create_product(self._business_id, command)
        elif isinstance(command, UpdateInventory):
            return engine.update_inventory(self._business_id, command)
        elif isinstance(command, CreateReminder):
            return engine.create_reminder(self._business_id, command)
        else:
            raise ValueError("Unknown command type")
