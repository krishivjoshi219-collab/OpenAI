"""Streamlit entry point for the AI Operations Employee MVP."""

import streamlit as st

from app.ui.components.layout import render_sidebar
from app.ui.components.pendo import inject_pendo
from app.ui.components.styles import apply_global_styles
from app.ui.components.toast import inject_toast_container
from app.ui.pages import (
    business_memory,
    code_viewer,
    customers,
    dashboard,
    government_assistant,
    home,
    invoices,
    onboarding,
    products,
    settings,
    voice_commands,
)


PAGE_RENDERERS = {
    "Home": home.render,
    "Onboarding": onboarding.render,
    "Business Dashboard": dashboard.render,
    "Customers": customers.render,
    "Products": products.render,
    "Invoices": invoices.render,
    "Business Memory": business_memory.render,
    "Government Assistant": government_assistant.render,
    "Voice Commands": voice_commands.render,
    "Settings": settings.render,
    "View Code": code_viewer.render,
}


def main() -> None:
    """Configure and render the selected presentation-only workspace page."""

    st.set_page_config(
        page_title="Aster Ops · AI Operations Employee",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()
    inject_pendo()
    inject_toast_container()
    selected_page = render_sidebar()
    PAGE_RENDERERS[selected_page]()


if __name__ == "__main__":
    main()
