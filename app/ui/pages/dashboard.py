"""Business dashboard layout."""

import streamlit as st

from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.widgets import Metric, render_metric, render_record_row


def render() -> None:
    """Render the dashboard's empty-but-useful initial state."""

    render_page_header(
        "Business dashboard",
        "A clear view of your operation.",
        "Once connected, this dashboard will surface revenue, customer activity, inventory signals, "
        "and work needing attention.",
    )
    render_section_title("This month")
    columns = st.columns(4, gap="medium")
    metrics = [
        Metric("Revenue", "$0", "Awaiting invoice data", "neutral"),
        Metric("Invoices paid", "0", "Awaiting invoice data", "neutral"),
        Metric("Customers", "0", "Awaiting customer data", "neutral"),
        Metric("Low stock", "0", "Awaiting inventory data", "neutral"),
    ]
    for column, metric in zip(columns, metrics, strict=True):
        with column:
            render_metric(metric)
    recent, tasks = st.columns([3, 2], gap="large")
    with recent:
        render_section_title("Recent activity")
        st.markdown('<div class="product-card">', unsafe_allow_html=True)
        render_record_row("No activity yet", "Your operational timeline will appear here.", "Waiting")
        st.markdown("</div>", unsafe_allow_html=True)
    with tasks:
        render_section_title("Attention needed")
        st.markdown(
            """
            <div class="product-card">
              <div class="row-primary">Your workspace is ready to configure</div>
              <div class="row-secondary">Complete onboarding to unlock a tailored operational
              overview.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
