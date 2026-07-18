"""Settings page layout."""

import streamlit as st

from app.ui.components.layout import render_page_header, render_section_title


def render() -> None:
    """Render presentation-only workspace settings."""

    render_page_header(
        "Settings",
        "Make the workspace yours.",
        "Manage your business profile, notifications, and the preferences that shape future operations "
        "support.",
    )
    render_section_title("Business profile")
    left, right = st.columns(2, gap="large")
    with left:
        st.text_input("Business name", placeholder="Your business name")
        st.text_input("Business email", placeholder="you@company.com")
    with right:
        st.selectbox("Default currency", ["USD — US Dollar", "EUR — Euro", "INR — Indian Rupee"])
        st.selectbox("Time zone", ["Asia/Kolkata", "Europe/London", "America/New_York"])
    render_section_title("Notifications")
    st.toggle("Operational summaries", value=True, help="A future summary of business activity.")
    st.toggle("Attention-needed alerts", value=True, help="A future alert for items requiring review.")
    st.button("Save preferences", type="primary")
