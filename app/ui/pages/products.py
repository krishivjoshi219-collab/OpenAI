"""Products page layout."""

import streamlit as st

from app.i18n import t
from app.ui.components.layout import render_page_header
from app.ui.components.widgets import render_empty_state


def render() -> None:
    """Render the product catalogue empty state."""

    render_page_header(
        t("products.eyebrow"),
        t("products.title"),
        t("products.subtitle"),
    )
    filter_column, action = st.columns([4, 1])
    with filter_column:
        st.text_input(
            "Search products",
            placeholder=t("products.search"),
            label_visibility="collapsed",
        )
    with action:
        if st.button(t("products.btn.add"), type="primary", width="stretch"):
            st.session_state["_nav_pending"] = "Onboarding"
            st.rerun()
    if render_empty_state(
        "◇",
        t("products.empty.title"),
        t("products.empty.body"),
        t("products.empty.btn"),
    ):
        st.session_state["_nav_pending"] = "Onboarding"
        st.rerun()

