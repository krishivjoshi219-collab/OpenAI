"""Database-backed operational dashboard read model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Business, Customer, Inventory, Invoice, InvoiceStatus, Product, Reminder


@dataclass(frozen=True)
class CustomerBalance:
    """An outstanding receivable grouped by customer."""

    customer_name: str
    amount: Decimal


@dataclass(frozen=True)
class InventoryAlert:
    """A product that has reached its configured reorder point."""

    product_name: str
    sku: str
    quantity_on_hand: Decimal
    reorder_level: Decimal


@dataclass(frozen=True)
class ActivityItem:
    """A recent business event suitable for a compact activity feed."""

    title: str
    detail: str
    occurred_at: datetime
    kind: str


@dataclass(frozen=True)
class DashboardSnapshot:
    """All values rendered by the business dashboard for one business."""

    business_name: str
    currency_code: str
    todays_sales: Decimal
    pending_payments: Decimal
    low_inventory: tuple[InventoryAlert, ...]
    customers_owing: tuple[CustomerBalance, ...]
    recent_activity: tuple[ActivityItem, ...]
    suggestions: tuple[str, ...]


class DashboardService:
    """Load a business-scoped operational overview without mutating any records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_businesses(self) -> list[Business]:
        """Return available workspaces for dashboard selection."""

        return list(self._session.scalars(select(Business).order_by(Business.name)))

    def snapshot(self, business_id: UUID, *, today: date | None = None) -> DashboardSnapshot:
        """Compute all dashboard values from records belonging to one business."""

        business = self._session.get(Business, business_id)
        if business is None:
            raise ValueError("Business not found.")
        day = today or date.today()
        day_start = datetime.combine(day, time.min)
        next_day = day_start + timedelta(days=1)
        todays_sales = self._money(
            self._session.scalar(
                select(func.coalesce(func.sum(Invoice.total), 0)).where(
                    Invoice.business_id == business_id,
                    Invoice.status == InvoiceStatus.PAID,
                    Invoice.updated_at >= day_start,
                    Invoice.updated_at < next_day,
                )
            )
        )
        pending_payments = self._money(
            self._session.scalar(
                select(func.coalesce(func.sum(Invoice.total), 0)).where(
                    Invoice.business_id == business_id,
                    Invoice.status == InvoiceStatus.ISSUED,
                )
            )
        )
        low_inventory = tuple(
            InventoryAlert(
                product.name, product.sku, inventory.quantity_on_hand, inventory.reorder_level
            )
            for inventory, product in self._session.execute(
                select(Inventory, Product)
                .join(Product, Inventory.product_id == Product.id)
                .where(
                    Inventory.business_id == business_id,
                    Inventory.reorder_level > 0,
                    Inventory.quantity_on_hand <= Inventory.reorder_level,
                )
                .order_by(Inventory.quantity_on_hand, Product.name)
            )
        )
        customers_owing = tuple(
            CustomerBalance(name, self._money(amount))
            for name, amount in self._session.execute(
                select(Customer.name, func.coalesce(func.sum(Invoice.total), 0))
                .join(Invoice, Invoice.customer_id == Customer.id)
                .where(
                    Customer.business_id == business_id,
                    Invoice.status == InvoiceStatus.ISSUED,
                )
                .group_by(Customer.id, Customer.name)
                .order_by(func.sum(Invoice.total).desc())
            )
        )
        activity = self._recent_activity(business_id)
        suggestions = self._suggestions(
            low_inventory, customers_owing, pending_payments, business.currency_code
        )
        return DashboardSnapshot(
            business_name=business.name,
            currency_code=business.currency_code,
            todays_sales=todays_sales,
            pending_payments=pending_payments,
            low_inventory=low_inventory,
            customers_owing=customers_owing,
            recent_activity=activity,
            suggestions=suggestions,
        )

    def _recent_activity(self, business_id: UUID) -> tuple[ActivityItem, ...]:
        invoices = self._session.scalars(
            select(Invoice)
            .where(Invoice.business_id == business_id)
            .order_by(Invoice.updated_at.desc())
            .limit(6)
        )
        customers = self._session.scalars(
            select(Customer)
            .where(Customer.business_id == business_id)
            .order_by(Customer.created_at.desc())
            .limit(6)
        )
        products = self._session.scalars(
            select(Product)
            .where(Product.business_id == business_id)
            .order_by(Product.created_at.desc())
            .limit(6)
        )
        reminders = self._session.scalars(
            select(Reminder)
            .where(Reminder.business_id == business_id)
            .order_by(Reminder.created_at.desc())
            .limit(6)
        )
        events = [
            *(
                ActivityItem(
                    f"Invoice {item.invoice_number}",
                    item.status.value.title(),
                    item.updated_at,
                    "invoice",
                )
                for item in invoices
            ),
            *(
                ActivityItem(item.name, "Customer added", item.created_at, "customer")
                for item in customers
            ),
            *(
                ActivityItem(item.name, f"Product added · {item.sku}", item.created_at, "product")
                for item in products
            ),
            *(
                ActivityItem(item.title, "Reminder created", item.created_at, "reminder")
                for item in reminders
            ),
        ]
        return tuple(sorted(events, key=lambda item: item.occurred_at, reverse=True)[:6])

    @staticmethod
    def _suggestions(
        low_inventory: tuple[InventoryAlert, ...],
        customers_owing: tuple[CustomerBalance, ...],
        pending_payments: Decimal,
        currency_code: str,
    ) -> tuple[str, ...]:
        suggestions: list[str] = []
        if low_inventory:
            suggestions.append(
                f"Reorder {low_inventory[0].product_name}; stock is at or below its reorder level."
            )
        if customers_owing:
            suggestions.append(
                f"Follow up with {customers_owing[0].customer_name} about their "
                "outstanding balance."
            )
        if pending_payments and not customers_owing:
            suggestions.append(
                f"Review {currency_code} {pending_payments:,.2f} in pending invoice payments."
            )
        if not suggestions:
            suggestions.append(
                "Operations look clear. Review recent activity and plan the next priority."
            )
        return tuple(suggestions[:3])

    @staticmethod
    def _money(value: Decimal | int | None) -> Decimal:
        return Decimal(str(value or 0))
