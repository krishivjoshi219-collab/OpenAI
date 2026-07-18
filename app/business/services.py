"""Business services that implement the engine's deterministic command methods."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.business.commands import (
    CreateCustomer,
    CreateInvoice,
    CreateInvoiceLine,
    CreateProduct,
    CreateReminder,
    UpdateInventory,
)
from app.models import Business, Customer, Inventory, Invoice, InvoiceItem, Product, Reminder, Supplier

_MONEY = Decimal("0.01")


class _BusinessScopedService:
    """Shared business ownership validation for application services."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _require_business(self, business_id: UUID) -> Business:
        business = self._session.get(Business, business_id)
        if business is None:
            raise ValueError("Business not found.")
        return business


class CustomerService(_BusinessScopedService):
    """Create and search business-scoped customers."""

    def create(self, business_id: UUID, command: CreateCustomer) -> Customer:
        """Create a customer after checking business-scoped email uniqueness."""

        self._require_business(business_id)
        name = _required_text(command.name, "Customer name")
        email = _optional_text(command.email)
        if email is not None and self._session.scalar(
            select(Customer).where(Customer.business_id == business_id, Customer.email == email)
        ):
            raise ValueError("A customer with this email already exists for this business.")
        customer = Customer(
            business_id=business_id,
            name=name,
            email=email,
            phone=_optional_text(command.phone),
            billing_address=_optional_text(command.billing_address),
        )
        self._session.add(customer)
        self._session.flush()
        return customer

    def search(self, business_id: UUID, query: str, *, limit: int = 25) -> list[Customer]:
        """Search customers by case-insensitive name or email."""

        _validate_limit(limit)
        statement = select(Customer).where(Customer.business_id == business_id)
        if term := query.strip():
            pattern = f"%{term}%"
            statement = statement.where(or_(Customer.name.ilike(pattern), Customer.email.ilike(pattern)))
        return list(self._session.scalars(statement.order_by(Customer.name).limit(limit)))


class ProductService(_BusinessScopedService):
    """Create and search business-scoped products."""

    def create(self, business_id: UUID, command: CreateProduct) -> Product:
        """Create a product and validate any assigned supplier belongs to the business."""

        self._require_business(business_id)
        sku = _required_text(command.sku, "Product SKU")
        if self._find_by_sku(business_id, sku) is not None:
            raise ValueError("A product with this SKU already exists for this business.")
        if command.supplier_id is not None:
            supplier = self._session.get(Supplier, command.supplier_id)
            if supplier is None or supplier.business_id != business_id:
                raise ValueError("Supplier not found for this business.")
        if command.unit_price < 0:
            raise ValueError("Product unit price cannot be negative.")
        product = Product(
            business_id=business_id,
            supplier_id=command.supplier_id,
            name=_required_text(command.name, "Product name"),
            sku=sku,
            unit_price=_money(command.unit_price),
            cost_price=_money(command.cost_price) if command.cost_price is not None else None,
            description=_optional_text(command.description),
        )
        self._session.add(product)
        self._session.flush()
        return product

    def search(self, business_id: UUID, query: str, *, limit: int = 25) -> list[Product]:
        """Search products by case-insensitive name or SKU."""

        _validate_limit(limit)
        statement = select(Product).where(Product.business_id == business_id)
        if term := query.strip():
            pattern = f"%{term}%"
            statement = statement.where(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
        return list(self._session.scalars(statement.order_by(Product.name).limit(limit)))

    def _find_by_sku(self, business_id: UUID, sku: str) -> Product | None:
        return self._session.scalar(
            select(Product).where(Product.business_id == business_id, Product.sku == sku)
        )


class InvoiceService(_BusinessScopedService):
    """Create invoice snapshots and calculate their financial totals."""

    def create(self, business_id: UUID, command: CreateInvoice) -> Invoice:
        """Create a complete invoice with validated customer and product references."""

        business = self._require_business(business_id)
        self._require_customer(business_id, command.customer_id)
        invoice_number = _required_text(command.invoice_number, "Invoice number")
        if self._session.scalar(
            select(Invoice).where(
                Invoice.business_id == business_id,
                Invoice.invoice_number == invoice_number,
            )
        ):
            raise ValueError("An invoice with this number already exists for this business.")
        if not command.lines:
            raise ValueError("An invoice must contain at least one line.")
        currency = (command.currency_code or business.currency_code).upper()
        if len(currency) != 3:
            raise ValueError("Invoice currency code must contain exactly three letters.")
        invoice = Invoice(
            business_id=business_id,
            customer_id=command.customer_id,
            invoice_number=invoice_number,
            status=command.status,
            issued_on=command.issued_on,
            due_on=command.due_on,
            currency_code=currency,
            subtotal=Decimal("0"),
            tax_total=Decimal("0"),
            total=Decimal("0"),
            notes=_optional_text(command.notes),
        )
        invoice.items = [self._create_line(business_id, index, line) for index, line in enumerate(command.lines, 1)]
        invoice.subtotal = sum((item.quantity * item.unit_price for item in invoice.items), Decimal("0"))
        invoice.subtotal = _money(invoice.subtotal)
        invoice.total = sum((item.line_total for item in invoice.items), Decimal("0"))
        invoice.total = _money(invoice.total)
        invoice.tax_total = _money(invoice.total - invoice.subtotal)
        self._session.add(invoice)
        self._session.flush()
        return invoice

    def _create_line(self, business_id: UUID, position: int, command: CreateInvoiceLine) -> InvoiceItem:
        if command.quantity <= 0:
            raise ValueError("Invoice line quantity must be greater than zero.")
        if command.tax_rate < 0:
            raise ValueError("Invoice line tax rate cannot be negative.")
        product = self._require_product(business_id, command.product_id) if command.product_id else None
        unit_price = command.unit_price if command.unit_price is not None else product.unit_price if product else None
        if unit_price is None or unit_price < 0:
            raise ValueError("Each invoice line requires a non-negative unit price or product.")
        description = command.description or (product.name if product else None)
        line_subtotal = command.quantity * unit_price
        line_total = line_subtotal * (Decimal("1") + command.tax_rate / Decimal("100"))
        return InvoiceItem(
            product=product,
            position=position,
            description=_required_text(description, "Invoice line description"),
            quantity=command.quantity,
            unit_price=_money(unit_price),
            tax_rate=command.tax_rate,
            line_total=_money(line_total),
        )

    def _require_customer(self, business_id: UUID, customer_id: UUID) -> Customer:
        customer = self._session.get(Customer, customer_id)
        if customer is None or customer.business_id != business_id:
            raise ValueError("Customer not found for this business.")
        return customer

    def _require_product(self, business_id: UUID, product_id: UUID) -> Product:
        product = self._session.get(Product, product_id)
        if product is None or product.business_id != business_id:
            raise ValueError("Product not found for this business.")
        return product


class InventoryService(_BusinessScopedService):
    """Create or update a product's current stock position."""

    def update(self, business_id: UUID, command: UpdateInventory) -> Inventory:
        """Set current quantity and optionally the reorder threshold."""

        self._require_business(business_id)
        product = self._session.get(Product, command.product_id)
        if product is None or product.business_id != business_id:
            raise ValueError("Product not found for this business.")
        if command.quantity_on_hand < 0:
            raise ValueError("Inventory quantity cannot be negative.")
        inventory = self._session.scalar(
            select(Inventory).where(
                Inventory.business_id == business_id,
                Inventory.product_id == product.id,
            )
        )
        if inventory is None:
            inventory = Inventory(
                business_id=business_id,
                product_id=product.id,
                quantity_on_hand=command.quantity_on_hand,
                reorder_level=command.reorder_level or Decimal("0"),
            )
            self._session.add(inventory)
        else:
            inventory.quantity_on_hand = command.quantity_on_hand
            if command.reorder_level is not None:
                inventory.reorder_level = command.reorder_level
        self._session.flush()
        return inventory


class ReminderService(_BusinessScopedService):
    """Create operational reminders for a business."""

    def create(self, business_id: UUID, command: CreateReminder) -> Reminder:
        """Create an incomplete reminder in the business workspace."""

        self._require_business(business_id)
        reminder = Reminder(
            business_id=business_id,
            title=_required_text(command.title, "Reminder title"),
            details=_optional_text(command.details),
            due_at=command.due_at,
        )
        self._session.add(reminder)
        self._session.flush()
        return reminder


def _required_text(value: str | None, field_name: str) -> str:
    """Normalize a required string command value."""

    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def _optional_text(value: str | None) -> str | None:
    """Normalize an optional string command value."""

    normalized = (value or "").strip()
    return normalized or None


def _money(value: Decimal) -> Decimal:
    """Round a monetary amount using standard commercial half-up rounding."""

    return value.quantize(_MONEY, rounding=ROUND_HALF_UP)


def _validate_limit(limit: int) -> None:
    """Validate bounded search result sizes."""

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
