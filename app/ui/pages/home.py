"""Home page for the AI operations workspace."""

import streamlit as st

from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.widgets import Metric, render_metric


def render() -> None:
    """Render the product landing experience."""

    render_page_header(
        "Your operations workspace",
        "Good morning, Alex.",
        "A calm place to see what matters, delegate routine work, and keep your business moving.",
    )
    st.write("")
    overview, assistant = st.columns([2.2, 1], gap="large")
    with overview:
        st.markdown(
            """
            <div class="action-card">
              <h3>Your AI operations employee is standing by.</h3>
              <p>Connect your business data during onboarding, then use this workspace to handle
              customers, invoices, inventory, and the details worth remembering.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Start onboarding", type="primary"):
            st.session_state["nav_selected_page"] = "Onboarding"
            st.rerun()
    with assistant:
        st.markdown(
            """
            <div class="product-card">
              <div class="eyebrow">Workspace status</div>
              <div class="metric-value">0 / 4</div>
              <div class="row-secondary">Onboarding steps completed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    render_section_title("At a glance")
    columns = st.columns(3, gap="medium")
    metrics = [
        Metric("Customers", "0", "Ready when you are", "neutral"),
        Metric("Open invoices", "0", "No action needed", "neutral"),
        Metric("Products tracked", "0", "Catalogue not connected", "neutral"),
    ]
    for column, metric in zip(columns, metrics, strict=True):
        with column:
            render_metric(metric)
    render_section_title("Suggested next step")
    st.markdown(
        """
        <div class="product-card">
          <div class="row-primary">Tell us about your business</div>
          <div class="row-secondary">Set your company name, operating currency, and the workflows
          you want help with.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

