"""Database-backed business dashboard."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import streamlit as st

from app.database.session import create_session_factory, session_scope
from app.models import Business
from app.services.dashboard import DashboardService, DashboardSnapshot
from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.widgets import render_empty_state


def render() -> None:
    """Render a live operational dashboard for the selected business workspace."""

    render_page_header(
        "Live operations",
        "Business dashboard",
        "A focused view of revenue, cash flow, stock, and the work worth your attention today.",
    )
    try:
        with session_scope(create_session_factory()) as session:
            service = DashboardService(session)
            businesses = service.list_businesses()
            if not businesses:
                render_empty_state(
                    "✦",
                    "Create a workspace to see your dashboard",
                    "Your sales, payments, inventory, and activity will appear here as soon as "
                    "business data exists.",
                    "Go to onboarding",
                )
                return
            selected_id = _select_business(businesses)
            snapshot = service.snapshot(selected_id)
    except Exception as error:
        st.error(f"We could not load the dashboard: {error}")
        return
    _render_snapshot(snapshot)


def _select_business(businesses: list[Business]) -> UUID:
    """Select a workspace while preserving the onboarding workspace when available."""

    ids = [business.id for business in businesses]
    current = st.session_state.get("onboarding_business_id")
    try:
        onboarding_id = UUID(current) if isinstance(current, str) else None
    except ValueError:
        onboarding_id = None
    default_index = ids.index(onboarding_id) if onboarding_id in ids else 0
    selected = st.selectbox(
        "Workspace",
        businesses,
        index=default_index,
        format_func=lambda business: business.name,
        label_visibility="collapsed",
    )
    return selected.id


def _render_snapshot(snapshot: DashboardSnapshot) -> None:
    """Render one fully populated dashboard snapshot with Streamlit-native components."""

    currency = snapshot.currency_code
    metrics = st.columns(4, gap="medium")
    with metrics[0]:
        st.metric(
            "Today’s sales",
            _money(snapshot.todays_sales, currency),
            help="Paid invoices updated today.",
        )
    with metrics[1]:
        st.metric(
            "Pending payments",
            _money(snapshot.pending_payments, currency),
            help="Issued invoices awaiting payment.",
        )
    with metrics[2]:
        st.metric(
            "Low inventory",
            len(snapshot.low_inventory),
            help="Products at or below their reorder level.",
        )
    with metrics[3]:
        st.metric(
            "Customers owing",
            len(snapshot.customers_owing),
            help="Customers with issued invoices awaiting payment.",
        )

    activity_column, suggestions_column = st.columns([1.45, 1], gap="large")
    with activity_column:
        render_section_title("Recent activity")
        with st.container(border=True):
            if snapshot.recent_activity:
                for item in snapshot.recent_activity:
                    left, right = st.columns([5, 1])
                    with left:
                        st.markdown(f"**{item.title}**  \n{item.detail}")
                    with right:
                        st.caption(_relative_time(item.occurred_at))
                    st.divider()
            else:
                st.caption("No activity recorded yet.")
    with suggestions_column:
        render_section_title("AI suggestions")
        with st.container(border=True):
            st.caption("Based on live business signals")
            for suggestion in snapshot.suggestions:
                st.markdown(f"💡 {suggestion}")
                st.divider()

    inventory_column, receivables_column = st.columns(2, gap="large")
    with inventory_column:
        render_section_title("Low inventory")
        _render_low_inventory(snapshot)
    with receivables_column:
        render_section_title("Customers owing money")
        _render_customers_owing(snapshot, currency)


def _render_low_inventory(snapshot: DashboardSnapshot) -> None:
    """Render low-stock products, or a calm no-action state."""

    with st.container(border=True):
        if not snapshot.low_inventory:
            st.success("Inventory levels are healthy.")
            return
        for item in snapshot.low_inventory[:5]:
            st.markdown(f"**{item.product_name}** · `{item.sku}`")
            st.caption(f"{item.quantity_on_hand} on hand · reorder at {item.reorder_level}")
            # Guard against reorder_level=0 to prevent ZeroDivisionError
            if item.reorder_level > 0:
                st.progress(min(float(item.quantity_on_hand / item.reorder_level), 1.0))
            else:
                st.progress(1.0)
            st.divider()


def _render_customers_owing(snapshot: DashboardSnapshot, currency: str) -> None:
    """Render the largest open customer balances."""

    with st.container(border=True):
        if not snapshot.customers_owing:
            st.success("No customer payments are currently pending.")
            return
        for item in snapshot.customers_owing[:5]:
            left, right = st.columns([3, 1])
            with left:
                st.markdown(f"**{item.customer_name}**")
                st.caption("Open issued invoices")
            with right:
                st.markdown(f"**{_money(item.amount, currency)}**")
            st.divider()


def _money(value: Decimal, currency: str) -> str:
    """Format a database money value consistently without locale dependencies."""

    return f"{currency} {value:,.2f}"


def _relative_time(value: datetime) -> str:
    """Create a compact, stable activity timestamp."""

    delta = datetime.now(value.tzinfo) - value
    if delta.days:
        return f"{delta.days}d ago"
    hours = int(delta.total_seconds() // 3600)
    return f"{max(hours, 0)}h ago"
