"""Stable external ID mappings between Aster Ops and Odoo records."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AsterOpsMapping(models.Model):
    """Maps Aster Ops external UUIDs to Odoo internal IDs."""

    _name = "aster.ops.mapping"
    _description = "Aster Ops External ID Mapping"
    _sql_constraints = [
        (
            "uniq_external_ref",
            "unique(company_id, external_system, external_model, external_id)",
            "External ID mapping must be unique per company and model.",
        ),
    ]

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    external_system = fields.Selection(
        [("aster_ops", "Aster Ops")],
        string="External System",
        required=True,
        default="aster_ops",
    )
    external_model = fields.Char(string="External Model", required=True)
    external_id = fields.Char(string="External ID", required=True)
    odoo_model = fields.Char(string="Odoo Model", required=True)
    odoo_id = fields.Integer(string="Odoo Record ID", required=True)
    active = fields.Boolean(string="Active", default=True)
    last_sync_at = fields.Datetime(string="Last Synced")
    metadata = fields.Text(string="Metadata")

    @api.depends("external_model", "external_id", "odoo_model", "odoo_id")
    def _compute_display_name(self) -> None:
        for record in self:
            record.display_name = (
                f"{record.external_model}[{record.external_id}] -> "
                f"{record.odoo_model}[{record.odoo_id}]"
            )

    def action_sync_pending(self) -> None:
        """Scheduled action placeholder for pending sync operations."""

        pending = self.search([("active", "=", True), ("last_sync_at", "=", False)])
        for mapping in pending:
            try:
                mapping._sync_single()
            except Exception as error:
                mapping.error_message = str(error)

    def _sync_single(self) -> None:
        """Perform a single record sync operation."""

        self.last_sync_at = fields.Datetime.now()
        self.env.cr.commit()

    def action_view_odoo_record(self) -> dict:
        """Open the linked Odoo record."""

        self.ensure_one()
        if not self.odoo_model or not self.odoo_id:
            raise UserError(_("No Odoo record linked to this mapping."))
        return {
            "type": "ir.actions.act_window",
            "res_model": self.odoo_model,
            "res_id": self.odoo_id,
            "view_mode": "form",
            "target": "current",
        }
