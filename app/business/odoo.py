"""Production-grade Odoo JSON-RPC gateway with retries, circuit breaker, and resilience."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app import pendo
from app.backend.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class OdooError(RuntimeError):
    """Raised when Odoo rejects or cannot complete an RPC request."""

    def __init__(self, message: str, *, odoo_error_code: str | None = None) -> None:
        super().__init__(message)
        self.odoo_error_code = odoo_error_code


class OdooAuthError(OdooError):
    """Raised when Odoo authentication fails."""


class OdooTransport(Protocol):
    """HTTP seam for Odoo's JSON-RPC endpoint."""

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a JSON-RPC payload and return the decoded response."""


class OdooGateway(Protocol):
    """Application-facing Odoo operation port used by the service classes."""

    def execute(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        """Execute an allowed Odoo model method."""


class UrlLibOdooTransport:
    """Standard-library HTTP transport with timeout and error normalization."""

    def __init__(self, *, timeout: int = 30) -> None:
        self._timeout = timeout

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as error:
            raise OdooError(f"Odoo HTTP error {error.code}: {error.reason}") from error
        except URLError as error:
            raise OdooError(f"Odoo connection failed: {error.reason}") from error
        except json.JSONDecodeError as error:
            raise OdooError(f"Odoo returned invalid JSON: {error}") from error
        decoded = json.loads(body)
        if not isinstance(decoded, dict):
            raise OdooError("Odoo returned a non-dict JSON-RPC response.")
        return decoded


class OdooJsonRpcClient:
    """Production-grade Odoo JSON-RPC client with authentication caching, retries, and circuit breaker."""

    def __init__(
        self,
        base_url: str,
        database: str,
        username: str,
        api_key: str,
        transport: OdooTransport | None = None,
        *,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        if not all([base_url.strip(), database.strip(), username.strip(), api_key.strip()]):
            raise ValueError("Odoo URL, database, username, and API key are required.")
        self._base_url = base_url.rstrip("/")
        self._database = database
        self._username = username
        self._api_key = api_key
        self._transport = transport or UrlLibOdooTransport()
        self._uid: int | None = None
        self._request_id = 0
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._breaker = circuit_breaker or CircuitBreaker(
            name="odoo_jsonrpc",
            failure_threshold=5,
            recovery_timeout=30.0,
        )

    def execute(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        """Execute an Odoo model method with retries and circuit breaker protection."""

        return self._breaker.call(self._execute_once, model, method, args, kwargs)

    def _execute_once(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        uid = self._authenticate()
        return self._rpc(
            "object",
            "execute_kw",
            [self._database, uid, self._api_key, model, method, args, kwargs],
        )

    def _authenticate(self) -> int:
        if self._uid is None:
            result = self._rpc(
                "common",
                "authenticate",
                [self._database, self._username, self._api_key, {}],
            )
            if not isinstance(result, int) or isinstance(result, bool):
                raise OdooAuthError(
                    "Odoo authentication failed. Check the database, user, and API key."
                )
            self._uid = result
        return self._uid

    def _rpc(self, service: str, method: str, arguments: list[Any]) -> Any:
        delay = self._base_delay
        last_error: OdooError | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._transport.post_json(
                    f"{self._base_url}/jsonrpc",
                    {
                        "jsonrpc": "2.0",
                        "method": "call",
                        "params": {"service": service, "method": method, "args": arguments},
                        "id": self._request_id,
                    },
                )
                self._request_id += 1
                return self._handle_response(response)
            except OdooAuthError:
                self._uid = None
                raise
            except OdooError as error:
                last_error = error
                logger.warning(
                    "Odoo RPC %s.%s failed (attempt %d/%d): %s",
                    service,
                    method,
                    attempt,
                    self._max_retries,
                    error,
                )
                if attempt < self._max_retries:
                    time.sleep(delay)
                    delay = min(delay * 2, self._max_delay)

        raise OdooError(f"Odoo RPC failed after {self._max_retries} attempts: {last_error}") from last_error

    def _handle_response(self, response: dict[str, Any]) -> Any:
        if error := response.get("error"):
            message = self._extract_error_message(error)
            code = self._extract_error_code(error)
            if code == 401 or "access" in message.lower():
                raise OdooAuthError(message, odoo_error_code=code)
            raise OdooError(message, odoo_error_code=code)
        if "result" not in response:
            raise OdooError("Odoo response did not include a result.")
        return response["result"]

    @staticmethod
    def _extract_error_message(error: Any) -> str:
        if isinstance(error, dict):
            data = error.get("data")
            if isinstance(data, dict):
                return str(data.get("message", error.get("message", "Unknown Odoo error")))
            return str(error.get("message", "Unknown Odoo error"))
        return str(error)

    @staticmethod
    def _extract_error_code(error: Any) -> str | None:
        if isinstance(error, dict):
            data = error.get("data")
            if isinstance(data, dict):
                return str(data.get("code"))
        return None


@dataclass(frozen=True)
class OdooCreateCustomer:
    """Input for creating an Odoo customer partner."""

    name: str
    email: str | None = None
    phone: str | None = None
    street: str | None = None


@dataclass(frozen=True)
class OdooInvoiceLine:
    """One Odoo customer-invoice line."""

    name: str
    quantity: float
    price_unit: float
    product_id: int | None = None


@dataclass(frozen=True)
class OdooCreateInvoice:
    """Input for creating a draft Odoo customer invoice."""

    partner_id: int
    lines: tuple[OdooInvoiceLine, ...]
    invoice_date: date | None = None
    invoice_date_due: date | None = None
    narration: str | None = None


@dataclass(frozen=True)
class OdooInventoryUpdate:
    """Input for applying an inventory count at one Odoo location."""

    product_id: int
    location_id: int
    quantity: float


@dataclass(frozen=True)
class OdooReminder:
    """Input for an Odoo scheduled activity/reminder."""

    res_model: str
    res_id: int
    activity_type_id: int
    summary: str
    note: str | None = None
    date_deadline: date | None = None
    user_id: int | None = None


class OdooCustomerService:
    """Customer operations mapped to Odoo's ``res.partner`` model."""

    def __init__(self, gateway: OdooGateway) -> None:
        self._gateway = gateway

    def create(self, command: OdooCreateCustomer) -> dict[str, Any]:
        """Create a customer partner and return its Odoo ID."""

        partner_id = self._gateway.execute(
            "res.partner",
            "create",
            [
                {
                    "name": command.name,
                    "email": command.email,
                    "phone": command.phone,
                    "street": command.street,
                    "customer_rank": 1,
                }
            ],
            {},
        )
        return {"id": partner_id, "name": command.name}

    def search(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        """Search Odoo customers by name or email."""

        result = self._gateway.execute(
            "res.partner",
            "search_read",
            [["|", ["name", "ilike", query], ["email", "ilike", query]]],
            {"fields": ["id", "name", "email", "phone"], "limit": limit},
        )
        return list(result)


class OdooInvoiceService:
    """Invoice creation and delivery operations for Odoo ``account.move`` records."""

    def __init__(self, gateway: OdooGateway) -> None:
        self._gateway = gateway

    def create(self, command: OdooCreateInvoice) -> dict[str, Any]:
        """Create a draft customer invoice with Odoo one2many line commands."""

        lines = [
            (
                0,
                0,
                {
                    "name": line.name,
                    "quantity": line.quantity,
                    "price_unit": line.price_unit,
                    "product_id": line.product_id,
                },
            )
            for line in command.lines
        ]
        invoice_id = self._gateway.execute(
            "account.move",
            "create",
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": command.partner_id,
                    "invoice_line_ids": lines,
                    "invoice_date": _date(command.invoice_date),
                    "invoice_date_due": _date(command.invoice_date_due),
                    "narration": command.narration,
                }
            ],
            {},
        )
        return {"id": invoice_id, "state": "draft"}

    def send(self, invoice_id: int) -> dict[str, Any]:
        """Ask Odoo to open its configured send-and-print invoice workflow."""

        result = self._gateway.execute("account.move", "action_send_and_print", [[invoice_id]], {})
        pendo.track(
            "odoo_invoice_sent",
            properties={
                "invoice_id": invoice_id,
                "odoo_action_result": str(result)[:200],
            },
        )
        return {"id": invoice_id, "odoo_action": result, "status": "requested"}


class OdooInventoryService:
    """Inventory-count updates mapped to Odoo ``stock.quant`` operations."""

    def __init__(self, gateway: OdooGateway) -> None:
        self._gateway = gateway

    def update(self, command: OdooInventoryUpdate) -> dict[str, Any]:
        """Set and apply a counted quantity for one product/location pair."""

        domain = [
            ["product_id", "=", command.product_id],
            ["location_id", "=", command.location_id],
        ]
        quant_ids = self._gateway.execute("stock.quant", "search", [domain], {"limit": 1})
        if quant_ids:
            quant_id = quant_ids[0]
            self._gateway.execute(
                "stock.quant", "write", [[quant_id], {"inventory_quantity": command.quantity}], {}
            )
        else:
            quant_id = self._gateway.execute(
                "stock.quant",
                "create",
                [
                    {
                        "product_id": command.product_id,
                        "location_id": command.location_id,
                        "inventory_quantity": command.quantity,
                    }
                ],
                {"context": {"inventory_mode": True}},
            )
        self._gateway.execute("stock.quant", "action_apply_inventory", [[quant_id]], {})
        return {"id": quant_id, "product_id": command.product_id, "quantity": command.quantity}


class OdooReminderService:
    """Reminder operations mapped to Odoo ``mail.activity`` records."""

    def __init__(self, gateway: OdooGateway) -> None:
        self._gateway = gateway

    def create(self, command: OdooReminder) -> dict[str, Any]:
        """Create a scheduled Odoo activity on a chosen business record."""

        model_ids = self._gateway.execute(
            "ir.model", "search", [["model", "=", command.res_model]], {"limit": 1}
        )
        if not model_ids:
            raise OdooError(f"Odoo model not found: {command.res_model}")
        activity_id = self._gateway.execute(
            "mail.activity",
            "create",
            [
                {
                    "res_model_id": model_ids[0],
                    "res_id": command.res_id,
                    "activity_type_id": command.activity_type_id,
                    "summary": command.summary,
                    "note": command.note,
                    "date_deadline": _date(command.date_deadline),
                    "user_id": command.user_id,
                }
            ],
            {},
        )
        return {"id": activity_id, "res_model": command.res_model, "res_id": command.res_id}


def _date(value: date | None) -> str | None:
    """Return Odoo's standard ISO date representation."""

    return value.isoformat() if value else None
