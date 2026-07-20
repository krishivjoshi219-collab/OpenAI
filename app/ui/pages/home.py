"""Home page for the AI operations workspace."""

import streamlit as st

from app.i18n import t
from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.widgets import Metric, render_metric


def render() -> None:
    """Render the product landing experience."""

    render_page_header(
        t("home.eyebrow"),
        t("home.title"),
        t("home.subtitle"),
    )
    st.write("")
    overview, assistant = st.columns([2.2, 1], gap="large")
    with overview:
        st.markdown(
            f"""
            <div class="action-card">
              <h3>{t("home.card.heading")}</h3>
              <p>{t("home.card.body")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(t("home.btn.start"), type="primary"):
            st.session_state["nav_selected_page"] = "Onboarding"
            st.rerun()
    with assistant:
        # Derive real onboarding progress from session state so the counter
        # stays accurate after the user completes steps.
        _biz_created = bool(st.session_state.get("onboarding_business_id"))
        _step = int(st.session_state.get("onboarding_step", 2)) if _biz_created else 0
        # step 2 = import screen (1 done), 3 = confirmed (2 done), 4 = complete (4 done)
        _steps_done = {0: 0, 2: 1, 3: 2, 4: 4}.get(_step, 1) if _biz_created else 0
        st.markdown(
            f"""
            <div class="product-card">
              <div class="eyebrow">{t("home.status.label")}</div>
              <div class="metric-value">{_steps_done} / 4</div>
              <div class="row-secondary">{t("home.status.steps")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    render_section_title(t("home.glance.title"))
    columns = st.columns(3, gap="medium")
    metrics = [
        Metric(t("home.metric.customers"), "0", t("home.metric.customers.sub"), "neutral"),
        Metric(t("home.metric.invoices"),  "0", t("home.metric.invoices.sub"),  "neutral"),
        Metric(t("home.metric.products"),  "0", t("home.metric.products.sub"),  "neutral"),
    ]
    for column, metric in zip(columns, metrics, strict=True):
        with column:
            render_metric(metric)
    render_section_title(t("home.next.title"))
    st.markdown(
        f"""
        <div class="product-card">
          <div class="row-primary">{t("home.next.primary")}</div>
          <div class="row-secondary">{t("home.next.secondary")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
