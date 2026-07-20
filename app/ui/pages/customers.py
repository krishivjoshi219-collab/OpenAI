"""Customers page layout."""

import streamlit as st

from app.i18n import t
from app.ui.components.layout import render_page_header
from app.ui.components.widgets import render_empty_state


def render() -> None:
    """Render the customer directory empty state."""

    render_page_header(
        t("customers.eyebrow"),
        t("customers.title"),
        t("customers.subtitle"),
    )
    controls, action = st.columns([4, 1])
    with controls:
        st.text_input(
            "Search customers",
            placeholder=t("customers.search"),
            label_visibility="collapsed",
        )
    with action:
        st.button(t("customers.btn.add"), type="primary", width="stretch")
    render_empty_state(
        "◌",
        t("customers.empty.title"),
        t("customers.empty.body"),
        t("customers.empty.btn"),
    )
