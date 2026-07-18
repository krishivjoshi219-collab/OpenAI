"""Python command façade intended for future AI tool adapters."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.business.commands import (
    CreateCustomer,
    CreateInvoice,
    CreateProduct,
    CreateReminder,
    UpdateInventory,
)
from app.business.services import (
    CustomerService,
    InventoryService,
    InvoiceService,
    ProductService,
    ReminderService,
)
from app.models import Customer, Inventory, Invoice, Product, Reminder


class BusinessEngine:
    """Expose deterministic business actions as small, AI-callable Python methods."""

    def __init__(self, session: Session) -> None:
        self.customers = CustomerService(session)
        self.products = ProductService(session)
        self.invoices = InvoiceService(session)
        self.inventory = InventoryService(session)
        self.reminders = ReminderService(session)

    def create_customer(self, business_id: UUID, command: CreateCustomer) -> Customer:
        """Create a customer."""

        return self.customers.create(business_id, command)

    def create_product(self, business_id: UUID, command: CreateProduct) -> Product:
        """Create a product."""

        return self.products.create(business_id, command)

    def create_invoice(self, business_id: UUID, command: CreateInvoice) -> Invoice:
        """Create an invoice with calculated totals."""

        return self.invoices.create(business_id, command)

    def update_inventory(self, business_id: UUID, command: UpdateInventory) -> Inventory:
        """Set a product's inventory position."""

        return self.inventory.update(business_id, command)

    def search_customers(self, business_id: UUID, query: str, *, limit: int = 25) -> list[Customer]:
        """Search customers by name or email."""

        return self.customers.search(business_id, query, limit=limit)

    def search_products(self, business_id: UUID, query: str, *, limit: int = 25) -> list[Product]:
        """Search products by name or SKU."""

        return self.products.search(business_id, query, limit=limit)

    def create_reminder(self, business_id: UUID, command: CreateReminder) -> Reminder:
        """Create an operational reminder."""

        return self.reminders.create(business_id, command)
