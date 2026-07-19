"""Shared navigation and page framing components."""

import streamlit as st


PAGES: dict[str, str] = {
    "Home": "✦  Home",
    "Onboarding": "◎  Onboarding",
    "Business Dashboard": "▦  Business Dashboard",
    "Customers": "◌  Customers",
    "Products": "◇  Products",
    "Invoices": "▤  Invoices",
    "Business Memory": "◒  Business Memory",
    "Government Assistant": "⌁  Government Assistant",
    "Voice Commands": "🎙  Voice Commands",
    "Settings": "⚙  Settings",
    "View Code": "⟨/⟩  View Code",
}


def render_sidebar() -> str:
    """Render product navigation and return the selected page name."""

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
              <span class="brand-mark">A</span><span class="brand-name">Aster Ops</span>
              <div class="brand-caption">AI Operations Employee</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        selected = st.radio(
            "Navigation",
            options=list(PAGES),
            format_func=lambda page: PAGES[page],
            label_visibility="collapsed",
        )
        st.markdown(
            """
            <div class="sidebar-note">
              <strong>Build Week MVP</strong><br>
              Your business workspace is ready for its first operational workflow.
            </div>
            """,
            unsafe_allow_html=True,
        )
    return selected


def render_page_header(eyebrow: str, title: str, subtitle: str) -> None:
    """Render a consistent page introduction."""

    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="page-title">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-subtitle">{subtitle}</p>', unsafe_allow_html=True)


def render_section_title(title: str) -> None:
    """Render a shared section heading."""

    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

