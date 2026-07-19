{
    "name": "Aster Ops Integration",
    "version": "18.0.1.0.0",
    "category": "Integration",
    "summary": "Integration bridge for Aster Ops AI Operations Employee",
    "description": """
Aster Ops Integration
=====================

This module provides a production-grade integration bridge between
Aster Ops AI Operations Employee and Odoo 18 CE/EE.

Features:
  - Audit log for all external API calls
  - Stable external ID mappings for customers, invoices, and products
  - Webhook endpoints for receiving events from Aster Ops
  - Scheduled actions for bidirectional sync
  - Access control rules for integration data
    """,
    "author": "Aster Ops",
    "website": "https://asterops.ai",
    "license": "LGPL-3",
    "depends": ["base", "account", "stock", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
    ],
    "assets": {},
    "application": False,
    "installable": True,
    "auto_install": False,
}
