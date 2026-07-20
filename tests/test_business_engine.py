"""Integration tests for the deterministic business-engine command surface."""

from decimal import Decimal

from app.business import (
    BusinessEngine,
    CreateCustomer,
    CreateInvoice,
    CreateInvoiceLine,
    CreateProduct,
    CreateReminder,
    UpdateInventory,
)
from app.database.base import Base
from app.models import Business
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_engine_creates_and_searches_operational_records() -> None:
    """The engine exposes the supported command set without AI dependencies."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        business = Business(name="Acme", slug="acme", currency_code="USD")
        session.add(business)
        session.flush()
        operations = BusinessEngine(session)
        customer = operations.create_customer(
            business.id, CreateCustomer(name="Ada Lovelace", email="ada@example.com")
        )
        product = operations.create_product(
            business.id,
            CreateProduct(name="Analytical Engine", sku="ENG-1", unit_price=Decimal("100")),
        )
        invoice = operations.create_invoice(
            business.id,
            CreateInvoice(
                customer_id=customer.id,
                invoice_number="INV-001",
                lines=(CreateInvoiceLine(product_id=product.id, quantity=Decimal("2")),),
            ),
        )
        inventory = operations.update_inventory(
            business.id,
            UpdateInventory(product_id=product.id, quantity_on_hand=Decimal("8")),
        )
        reminder = operations.create_reminder(
            business.id, CreateReminder(title="Follow up on INV-001")
        )

        assert invoice.total == Decimal("200.00")
        assert inventory.quantity_on_hand == Decimal("8")
        assert reminder.is_completed is False
        assert operations.search_customers(business.id, "Ada") == [customer]
        assert operations.search_products(business.id, "ENG-1") == [product]
