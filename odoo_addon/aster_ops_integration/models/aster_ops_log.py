"""Audit log for external Aster Ops API calls."""

from odoo import api, fields, models


class AsterOpsLog(models.Model):
    """Immutable audit record for every external integration call."""

    _name = "aster.ops.log"
    _description = "Aster Ops Integration Log"
    _order = "created_at desc"

    name = fields.Char(
        string="Reference",
        required=True,
        default="/",
        copy=False,
    )
    direction = fields.Selection(
        [
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
        ],
        string="Direction",
        required=True,
    )
    endpoint = fields.Char(string="Endpoint", required=True)
    method = fields.Char(string="HTTP Method", default="POST")
    status_code = fields.Integer(string="Status Code")
    request_payload = fields.Text(string="Request Payload")
    response_payload = fields.Text(string="Response Payload")
    error_message = fields.Text(string="Error")
    latency_ms = fields.Float(string="Latency (ms)")
    created_at = fields.Datetime(string="Created At", default=fields.Datetime.now, readonly=True)
    res_model = fields.Char(string="Related Model")
    res_id = fields.Integer(string="Related Record ID")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> "AsterOpsLog":
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("aster.ops.log") or "/"
        return super().create(vals_list)
