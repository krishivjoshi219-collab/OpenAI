"""Create the initial operations data model.

Revision ID: 20260718_0001
Revises:
Create Date: 2026-07-18 00:00:00
"""

# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260718_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    """Create all tables required by the initial database layer."""

    op.create_table(
        "businesses", *_audit_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255)), sa.Column("phone", sa.String(length=50)),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_businesses_slug", "businesses", ["slug"])
    op.create_table(
        "customers", *_audit_columns(),
        sa.Column("business_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255)), sa.Column("phone", sa.String(length=50)),
        sa.Column("billing_address", sa.String(length=500)),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "email", name="uq_customers_business_email"),
    )
    op.create_table(
        "suppliers", *_audit_columns(),
        sa.Column("business_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255)), sa.Column("phone", sa.String(length=50)), sa.Column("address", sa.String(length=500)),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "email", name="uq_suppliers_business_email"),
    )
    op.create_table(
        "products", *_audit_columns(),
        sa.Column("business_id", sa.Uuid(), nullable=False), sa.Column("supplier_id", sa.Uuid()),
        sa.Column("name", sa.String(length=255), nullable=False), sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=2000)), sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cost_price", sa.Numeric(precision=12, scale=2)), sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),
    )
    op.create_table(
        "invoices", *_audit_columns(),
        sa.Column("business_id", sa.Uuid(), nullable=False), sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_number", sa.String(length=100), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "ISSUED", "PAID", "VOID", name="invoice_status", native_enum=False), nullable=False),
        sa.Column("issued_on", sa.Date()), sa.Column("due_on", sa.Date()), sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False), sa.Column("tax_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False), sa.Column("notes", sa.String(length=2000)),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "invoice_number", name="uq_invoices_business_number"),
    )
    op.create_table(
        "inventory", *_audit_columns(),
        sa.Column("business_id", sa.Uuid(), nullable=False), sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(precision=14, scale=3), nullable=False), sa.Column("reorder_level", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "product_id", name="uq_inventory_business_product"),
    )
    op.create_table(
        "invoice_items", *_audit_columns(),
        sa.Column("invoice_id", sa.Uuid(), nullable=False), sa.Column("product_id", sa.Uuid()), sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False), sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False), sa.Column("tax_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", "position", name="uq_invoice_items_position"),
    )
    op.create_table(
        "business_memories", *_audit_columns(),
        sa.Column("business_id", sa.Uuid(), nullable=False), sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False), sa.Column("source", sa.String(length=100)), sa.Column("attributes", sa.JSON()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_memories_category", "business_memories", ["category"])
    op.create_table(
        "settings", *_audit_columns(),
        sa.Column("business_id", sa.Uuid(), nullable=False), sa.Column("values", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id"),
    )


def downgrade() -> None:
    """Drop the initial operations schema in dependency order."""

    op.drop_table("settings")
    op.drop_index("ix_business_memories_category", table_name="business_memories")
    op.drop_table("business_memories")
    op.drop_table("invoice_items")
    op.drop_table("inventory")
    op.drop_table("invoices")
    op.drop_table("products")
    op.drop_table("suppliers")
    op.drop_table("customers")
    op.drop_index("ix_businesses_slug", table_name="businesses")
    op.drop_table("businesses")
