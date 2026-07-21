"""Business memory page layout."""

import streamlit as st

from app.i18n import t
from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.widgets import render_empty_state


def render() -> None:
    """Render the durable business context workspace."""

    render_page_header(
        t("memory.eyebrow"),
        t("memory.title"),
        t("memory.subtitle"),
    )
    st.markdown(
        f"""
        <div class="action-card">
          <h3>{t("memory.card.heading")}</h3>
          <p>{t("memory.card.body")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_section_title(t("memory.section.saved"))
    render_empty_state(
        "◒",
        t("memory.empty.title"),
        t("memory.empty.body"),
        t("memory.empty.btn"),
    )
