"""Products page layout."""

import streamlit as st

from app.ui.components.layout import render_page_header
from app.ui.components.widgets import render_empty_state


def render() -> None:
    """Render the product catalogue empty state."""

    render_page_header(
        "Product catalogue",
        "What your business sells.",
        "Build a simple, reliable view of products, suppliers, pricing, and stock positions.",
    )
    filter_column, action = st.columns([4, 1])
    with filter_column:
        st.text_input("Search products", placeholder="Search products or SKUs", label_visibility="collapsed")
    with action:
        st.button("Add product", type="primary", use_container_width=True)
    render_empty_state(
        "◇",
        "No products yet",
        "Create a product to establish your catalogue and start tracking operational inventory.",
        "Create a product",
    )
