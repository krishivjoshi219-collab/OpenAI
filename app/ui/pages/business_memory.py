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
        """
        <div class="action-card">
          <h3>Memory stays business-scoped.</h3>
          <p>As you add context, it will remain visible and manageable here. Nothing is hidden behind
          the assistant.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_section_title("Saved context")
    if render_empty_state(
        "◒",
        "No saved context yet",
        "Add useful facts such as operating preferences, customer commitments, or recurring business "
        "routines.",
        "Add business context",
    ):
        st.session_state["_nav_pending"] = "Voice Commands"
        st.rerun()

