"""Invoices page layout."""

import streamlit as st

from app.ui.components.layout import render_page_header
from app.ui.components.widgets import render_empty_state


def render() -> None:
    """Render the invoice workspace empty state."""

    render_page_header(
        "Invoices",
        "Keep cash flow in view.",
        "Create, review, and follow the invoices that move your business forward.",
    )
    filter_column, action = st.columns([4, 1])
    with filter_column:
        st.selectbox("Status", ["All invoices", "Draft", "Issued", "Paid", "Void"], label_visibility="collapsed")
    with action:
        st.button("Create invoice", type="primary", use_container_width=True)
    render_empty_state(
        "▤",
        "No invoices to show",
        "When you create an invoice, its status, value, and due date will be easy to follow here.",
        "Create your first invoice",
    )
