"""Webhook and API controllers for Aster Ops integration."""

from odoo import http
from odoo.http import request


class AsterOpsController(http.Controller):
    """Receive webhook events from Aster Ops and expose health checks."""

    @http.route(
        "/aster_ops/webhook/inbound",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def webhook_inbound(self) -> dict[str, Any]:
        """Receive JSON webhook payloads from Aster Ops."""

        payload = request.jsonrequest
        if not payload:
            return {"status": "error", "message": "Empty payload"}

        log_model = request.env["aster.ops.log"].sudo()
        log_model.create(
            {
                "direction": "inbound",
                "endpoint": "/aster_ops/webhook/inbound",
                "method": "POST",
                "request_payload": str(payload),
                "status_code": 200,
                "response_payload": '{"status": "accepted"}',
            }
        )
        return {"status": "accepted"}

    @http.route(
        "/aster_ops/health",
        type="json",
        auth="none",
        methods=["GET"],
    )
    def health_check(self) -> dict[str, Any]:
        """Lightweight health check for load balancers and monitoring."""

        return {
            "status": "ok",
            "module": "aster_ops_integration",
            "odoo_version": request.env["ir.module.module"].search_count([]),
        }
