"""Customers page layout."""

import streamlit as st

from app.ui.components.layout import render_page_header
from app.ui.components.widgets import render_empty_state


def render() -> None:
    """Render the customer directory empty state."""

    render_page_header(
        "Customer relationships",
        "Customers, in one place.",
        "Keep the people you serve close at hand. Customer activity and context will live here.",
    )
    controls, action = st.columns([4, 1])
    with controls:
        st.text_input("Search customers", placeholder="Search by name or email", label_visibility="collapsed")
    with action:
        st.button("Add customer", type="primary", width="stretch")
    render_empty_state(
        "◌",
        "Your customer list is empty",
        "Add your first customer to begin building a clearer view of relationships and revenue.",
        "Add your first customer",
    )
