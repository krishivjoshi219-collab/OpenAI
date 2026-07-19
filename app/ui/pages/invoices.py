"""Invoices page — list, preview, and export invoices as JPG or AVIF images."""

from __future__ import annotations

from decimal import Decimal

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database.session import create_session_factory, session_scope
from app.models.business import Business
from app.models.invoice import Invoice
from app.models.enums import InvoiceStatus
from app.services.invoice_image import InvoiceImageData, InvoiceImageRenderer, LineItemData
from app.services.invoice_pdf import InvoicePdfRenderer
from app.ui.components.layout import render_page_header
from app.ui.components.widgets import render_empty_state, render_skeleton_card


_STATUS_TONE: dict[str, str] = {
    "DRAFT":  "neutral",
    "ISSUED": "positive",
    "PAID":   "positive",
    "VOID":   "neutral",
}

_RENDERER     = InvoiceImageRenderer()
_PDF_RENDERER = InvoicePdfRenderer()


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the invoice workspace with live data and image-export actions."""

    render_page_header(
        "Invoices",
        "Keep cash flow in view.",
        "Review invoices and download them as JPG or AVIF images for sharing or archiving.",
    )

    factory = create_session_factory()
    with session_scope(factory) as session:
        business = session.scalar(select(Business).limit(1))
        if business is None:
            _render_no_business()
            return

        status_filter, col_action = st.columns([4, 1])
        with status_filter:
            chosen = st.selectbox(
                "Status",
                ["All", "Draft", "Issued", "Paid", "Void"],
                label_visibility="collapsed",
                key="invoice_status_filter",
            )
        with col_action:
            st.button("Create invoice", type="primary", width="stretch", disabled=True)

        stmt = (
            select(Invoice)
            .where(Invoice.business_id == business.id)
            .options(joinedload(Invoice.customer), joinedload(Invoice.items))
            .order_by(Invoice.created_at.desc())
        )
        if chosen != "All":
            stmt = stmt.where(Invoice.status == InvoiceStatus[chosen.upper()])

        invoices = list(session.scalars(stmt).unique())

    if not invoices:
        render_empty_state(
            "▤",
            "No invoices to show",
            "When you create an invoice, its status, value, and due date will be easy to follow here.",
            "Create your first invoice",
        )
        return

    _render_invoice_list(invoices, business.name, business.email)


# ---------------------------------------------------------------------------
# Sub-renderers
# ---------------------------------------------------------------------------


def _render_no_business() -> None:
    render_empty_state(
        "◎",
        "Complete onboarding first",
        "Set up your business workspace in the Onboarding section, then your invoices will appear here.",
        "Go to Onboarding",
    )


def _render_invoice_list(
    invoices: list[Invoice],
    business_name: str,
    business_email: str | None,
) -> None:
    """Render every invoice as a card row with JPG / AVIF download buttons."""

    st.markdown(f"**{len(invoices)} invoice{'s' if len(invoices) != 1 else ''}**")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    for index, inv in enumerate(invoices, start=1):
        _render_invoice_row(inv, business_name, business_email, index=index)


def _render_invoice_row(
    inv: Invoice,
    business_name: str,
    business_email: str | None,
    *,
    index: int = 0,
) -> None:
    status_str = inv.status.value if hasattr(inv.status, "value") else str(inv.status)
    customer_name = inv.customer.name if inv.customer else "Unknown customer"
    sym = inv.currency_code[:1] if inv.currency_code else "$"
    total_str = f"{sym}{inv.total:,.2f}"
    due_str = inv.due_on.strftime("%d %b %Y") if inv.due_on else "No due date"

    with st.container():
        col_info, col_jpg, col_avif, col_pdf = st.columns([5, 1, 1, 1])

        with col_info:
            st.markdown(
                f"""
                <div class="table-row" style="animation: pageFadeIn .4s ease-out;">
                  <div class="row-primary">**{inv.invoice_number}** &nbsp;·&nbsp; {customer_name} &nbsp;·&nbsp; `{status_str}` &nbsp;·&nbsp; {total_str} &nbsp;·&nbsp; Due {due_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        data = _build_image_data(inv, business_name, business_email)

        with col_jpg:
            st.download_button(
                label="⬇ JPG",
                data=_RENDERER.to_bytes(data, fmt="jpeg"),
                file_name=f"invoice_{inv.invoice_number}.jpg",
                mime="image/jpeg",
                width="stretch",
                key=f"jpg_{inv.id}",
            )

        with col_avif:
            st.download_button(
                label="⬇ AVIF",
                data=_RENDERER.to_bytes(data, fmt="avif"),
                file_name=f"invoice_{inv.invoice_number}.avif",
                mime="image/avif",
                width="stretch",
                key=f"avif_{inv.id}",
            )

        with col_pdf:
            st.download_button(
                label="⬇ PDF",
                data=_PDF_RENDERER.to_bytes(data),
                file_name=f"invoice_{inv.invoice_number}.pdf",
                mime="application/pdf",
                width="stretch",
                key=f"pdf_{inv.id}",
            )

        st.divider()


def _build_image_data(
    inv: Invoice,
    business_name: str,
    business_email: str | None,
) -> InvoiceImageData:
    customer = inv.customer
    items = [
        LineItemData(
            description=it.description,
            quantity=it.quantity,
            unit_price=it.unit_price,
            tax_rate=it.tax_rate,
            line_total=it.line_total,
        )
        for it in (inv.items or [])
    ]
    status_str = inv.status.value if hasattr(inv.status, "value") else str(inv.status)
    return InvoiceImageData(
        invoice_number=inv.invoice_number,
        status=status_str.upper(),
        currency_code=inv.currency_code,
        subtotal=inv.subtotal or Decimal("0"),
        tax_total=inv.tax_total or Decimal("0"),
        total=inv.total or Decimal("0"),
        business_name=business_name,
        business_email=business_email,
        customer_name=customer.name if customer else "—",
        customer_email=customer.email if customer else None,
        customer_address=customer.billing_address if customer else None,
        issued_on=inv.issued_on,
        due_on=inv.due_on,
        notes=inv.notes,
        items=items,
    )
