"""Integration tests for SQLAlchemy mappings and repository behavior."""

from decimal import Decimal
from uuid import UUID

from app.database.base import Base
from app.database.repositories import Repository
from app.models import Business, Customer, Inventory, Invoice, InvoiceItem, Product, Supplier
from app.models.enums import InvoiceStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_persists_business_graph_with_uuid_ids() -> None:
    """The initial domain graph persists correctly on SQLite."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        business = Business(name="Acme Ltd", slug="acme", currency_code="USD")
        supplier = Supplier(business=business, name="Source Co")
        product = Product(
            business=business,
            supplier=supplier,
            name="Widget",
            sku="WIDGET-001",
            unit_price=Decimal("19.99"),
        )
        customer = Customer(business=business, name="Taylor Example")
        invoice = Invoice(
            business=business,
            customer=customer,
            invoice_number="INV-001",
            currency_code="USD",
            status=InvoiceStatus.DRAFT,
            subtotal=Decimal("19.99"),
            tax_total=Decimal("0"),
            total=Decimal("19.99"),
        )
        invoice.items.append(
            InvoiceItem(
                product=product,
                position=1,
                description="Widget",
                quantity=Decimal("1"),
                unit_price=Decimal("19.99"),
                tax_rate=Decimal("0"),
                line_total=Decimal("19.99"),
            )
        )
        inventory = Inventory(business=business, product=product, quantity_on_hand=Decimal("10"))
        session.add_all([invoice, inventory])
        session.commit()

        assert isinstance(business.id, UUID)
        assert invoice.customer is customer
        assert product.inventory is inventory
        assert invoice.items[0].product is product


def test_repository_stages_and_reads_entities() -> None:
    """The generic repository delegates persistence while the caller owns commits."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session, Business)
        business = repository.add(Business(name="Acme Ltd", slug="acme"))
        repository.flush()

        assert repository.get(business.id) is business
        assert repository.list() == [business]
