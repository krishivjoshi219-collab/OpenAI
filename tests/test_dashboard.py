"""Tests for the database-backed dashboard read model."""

from datetime import date, datetime
from decimal import Decimal

from app.database.base import Base
from app.models import Business, Customer, Inventory, Invoice, InvoiceStatus, Product, Reminder
from app.services.dashboard import DashboardService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_dashboard_snapshot_uses_only_selected_business_data() -> None:
    """Dashboard cards, tables, activity, and suggestions are derived from database records."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    today = date(2026, 7, 18)
    timestamp = datetime(2026, 7, 18, 10, 30)
    with Session(engine) as session:
        business = Business(name="Acme", slug="acme", currency_code="USD")
        other = Business(name="Other", slug="other", currency_code="USD")
        customer = Customer(business=business, name="Ada")
        product = Product(business=business, name="Widget", sku="W-1", unit_price=Decimal("20"))
        paid = Invoice(
            business=business,
            customer=customer,
            invoice_number="INV-PAID",
            currency_code="USD",
            status=InvoiceStatus.PAID,
            subtotal=Decimal("125"),
            tax_total=Decimal("0"),
            total=Decimal("125"),
            updated_at=timestamp,
        )
        pending = Invoice(
            business=business,
            customer=customer,
            invoice_number="INV-DUE",
            currency_code="USD",
            status=InvoiceStatus.ISSUED,
            subtotal=Decimal("80"),
            tax_total=Decimal("0"),
            total=Decimal("80"),
            updated_at=timestamp,
        )
        inventory = Inventory(
            business=business,
            product=product,
            quantity_on_hand=Decimal("2"),
            reorder_level=Decimal("5"),
        )
        reminder = Reminder(business=business, title="Call Ada", created_at=timestamp)
        unrelated_customer = Customer(business=other, name="Ignore me")
        unrelated_invoice = Invoice(
            business=other,
            customer=unrelated_customer,
            invoice_number="OTHER-1",
            currency_code="USD",
            status=InvoiceStatus.ISSUED,
            subtotal=Decimal("999"),
            tax_total=Decimal("0"),
            total=Decimal("999"),
            updated_at=timestamp,
        )
        session.add_all([paid, pending, inventory, reminder, unrelated_invoice])
        session.commit()

        snapshot = DashboardService(session).snapshot(business.id, today=today)

    assert snapshot.todays_sales == Decimal("125")
    assert snapshot.pending_payments == Decimal("80")
    assert snapshot.low_inventory[0].sku == "W-1"
    assert snapshot.customers_owing[0].customer_name == "Ada"
    assert snapshot.customers_owing[0].amount == Decimal("80")
    assert any(item.title == "Call Ada" for item in snapshot.recent_activity)
    assert "Reorder Widget" in snapshot.suggestions[0]
