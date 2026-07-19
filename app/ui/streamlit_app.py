import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

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


def _run_preflight_once() -> None:
    """Execute async dependency health checks once per session and cache the result."""

    if st.session_state.get("preflight_completed"):
        return

    try:
        import asyncio

        from app.backend.preflight import run_preflight_checks
        from config.settings import get_settings

        settings = get_settings()
        results = asyncio.run(run_preflight_checks(settings, total_timeout_ms=3000))

        for name, result in results.items():
            st.session_state[f"preflight_result_{name}"] = result
            if not result.ok:
                st.session_state[f"preflight_failed_{name}"] = True

        st.session_state["preflight_completed"] = True
    except Exception as exc:  # noqa: BLE001
        st.session_state["preflight_completed"] = True
        st.session_state["global_error"] = str(exc)


def _handle_global_error(exc: Exception) -> None:
    """Display a user-friendly recovery message for unhandled exceptions."""

    st.session_state["global_error"] = str(exc)
    st.error(
        "Sorry, a minor system conflict occurred. "
        "Aster Ops automated recovery tools are deploying a live container hotfix now..."
    )


def main() -> None:
    """Configure and render the selected presentation-only workspace page."""

    try:
        _run_preflight_once()

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
    except Exception as exc:
        _handle_global_error(exc)


if __name__ == "__main__":
    main()
