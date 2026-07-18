"""Application service for confirming onboarding extraction previews."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Business, Customer, Inventory, Invoice, Product
from app.onboarding.extraction import (
    CustomerRecord,
    ExtractedRecord,
    ExtractionPreview,
    InvoiceRecord,
    ProductRecord,
    StockRecord,
)


@dataclass(frozen=True)
class ImportConfirmation:
    """Summary returned after an accepted preview is persisted."""

    created: int
    updated: int
    skipped: int
    messages: list[str] = field(default_factory=list)


class OnboardingImportService:
    """Persist reviewed onboarding data while keeping extraction provider-independent."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_business(self, name: str, email: str | None, currency_code: str) -> Business:
        """Create the business container required before importing operational records."""

        slug = _slugify(name)
        existing = self._session.scalar(select(Business).where(Business.slug == slug))
        if existing is not None:
            raise ValueError(
                "A business with this name already exists. Choose a more specific name."
            )
        business = Business(
            name=name.strip(),
            slug=slug,
            email=email.strip() if email else None,
            currency_code=currency_code,
        )
        self._session.add(business)
        self._session.flush()
        return business

    def confirm(self, business_id: UUID, preview: ExtractionPreview) -> ImportConfirmation:
        """Store all records in a supported, user-reviewed extraction preview."""

        if not preview.is_supported:
            raise ValueError(
                "This file format cannot be confirmed until an extraction provider is installed."
            )
        self._require_business(business_id)
        summary = _ImportSummary()
        for record in preview.records:
            self._persist_record(business_id, record, summary)
            self._session.flush()
        self._session.flush()
        return summary.freeze()

    def _persist_record(
        self, business_id: UUID, record: ExtractedRecord, summary: _ImportSummary
    ) -> None:
        if isinstance(record, CustomerRecord):
            self._persist_customer(business_id, record, summary)
        elif isinstance(record, ProductRecord):
            self._persist_product(business_id, record, summary)
        elif isinstance(record, StockRecord):
            self._persist_stock(business_id, record, summary)
        elif isinstance(record, InvoiceRecord):
            self._persist_invoice(business_id, record, summary)

    def _require_business(self, business_id: UUID) -> Business:
        business = self._session.get(Business, business_id)
        if business is None:
            raise ValueError("The onboarding business could not be found.")
        return business

    def _persist_customer(
        self, business_id: UUID, record: CustomerRecord, summary: _ImportSummary
    ) -> Customer:
        customer = self._find_customer(business_id, record.email, record.name)
        if customer is None:
            customer = Customer(business_id=business_id, name=record.name, email=record.email)
            self._session.add(customer)
            summary.created += 1
        else:
            summary.updated += 1
        customer.phone = record.phone or customer.phone
        customer.billing_address = record.billing_address or customer.billing_address
        return customer

    def _persist_product(
        self, business_id: UUID, record: ProductRecord, summary: _ImportSummary
    ) -> Product:
        product = self._find_product(business_id, record.sku)
        if product is None:
            product = Product(
                business_id=business_id,
                name=record.name,
                sku=record.sku,
                unit_price=record.unit_price,
                cost_price=record.cost_price,
                description=record.description,
            )
            self._session.add(product)
            summary.created += 1
        else:
            product.name = record.name
            product.unit_price = record.unit_price
            product.cost_price = record.cost_price
            product.description = record.description
            summary.updated += 1
        return product

    def _persist_stock(
        self, business_id: UUID, record: StockRecord, summary: _ImportSummary
    ) -> None:
        product = self._find_product(business_id, record.sku)
        if product is None:
            summary.skipped += 1
            summary.messages.append(
                f"Skipped stock for SKU {record.sku}: product was not imported."
            )
            return
        inventory = self._session.scalar(
            select(Inventory).where(
                Inventory.business_id == business_id,
                Inventory.product_id == product.id,
            )
        )
        if inventory is None:
            inventory = Inventory(
                business_id=business_id,
                product=product,
                quantity_on_hand=record.quantity_on_hand,
                reorder_level=record.reorder_level,
            )
            self._session.add(inventory)
            summary.created += 1
        else:
            inventory.quantity_on_hand = record.quantity_on_hand
            inventory.reorder_level = record.reorder_level
            summary.updated += 1

    def _persist_invoice(
        self, business_id: UUID, record: InvoiceRecord, summary: _ImportSummary
    ) -> None:
        customer = self._persist_customer(
            business_id,
            CustomerRecord(name=record.customer_name, email=record.customer_email),
            summary,
        )
        invoice = self._session.scalar(
            select(Invoice).where(
                Invoice.business_id == business_id,
                Invoice.invoice_number == record.invoice_number,
            )
        )
        if invoice is None:
            invoice = Invoice(
                business_id=business_id,
                customer=customer,
                invoice_number=record.invoice_number,
                status=record.status,
                issued_on=record.issued_on,
                due_on=record.due_on,
                currency_code=record.currency_code,
                subtotal=record.total,
                tax_total=Decimal("0"),
                total=record.total,
            )
            self._session.add(invoice)
            summary.created += 1
        else:
            invoice.customer = customer
            invoice.status = record.status
            invoice.issued_on = record.issued_on
            invoice.due_on = record.due_on
            invoice.currency_code = record.currency_code
            invoice.subtotal = record.total
            invoice.total = record.total
            summary.updated += 1

    def _find_customer(
        self, business_id: UUID, email: str | None, name: str
    ) -> Customer | None:
        if email is not None:
            customer = self._session.scalar(
                select(Customer).where(Customer.business_id == business_id, Customer.email == email)
            )
            if customer is not None:
                return customer
        return self._session.scalar(
            select(Customer).where(Customer.business_id == business_id, Customer.name == name)
        )

    def _find_product(self, business_id: UUID, sku: str) -> Product | None:
        return self._session.scalar(
            select(Product).where(Product.business_id == business_id, Product.sku == sku)
        )


@dataclass
class _ImportSummary:
    """Mutable internal accumulator for a single confirmation transaction."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    messages: list[str] = field(default_factory=list)

    def freeze(self) -> ImportConfirmation:
        """Return an immutable result for presentation code."""

        return ImportConfirmation(
            created=self.created,
            updated=self.updated,
            skipped=self.skipped,
            messages=self.messages,
        )


def _slugify(value: str) -> str:
    """Create a stable URL-safe business identifier from a display name."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("Business name must include at least one letter or number.")
    return slug[:100]
