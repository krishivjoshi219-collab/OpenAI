"""Shared navigation and page framing components."""

import streamlit as st

from app import pendo
from app.i18n import t
from app.ui.components.sidebar_keys import render_byok_section

# Page keys → i18n key (kept as a stable mapping so streamlit_app.py can
# match the returned value against PAGE_RENDERERS).
_NAV_KEYS: dict[str, str] = {
    "Home":                "nav.home",
    "Onboarding":          "nav.onboarding",
    "Business Dashboard":  "nav.dashboard",
    "Customers":           "nav.customers",
    "Products":            "nav.products",
    "Invoices":            "nav.invoices",
    "Business Memory":     "nav.memory",
    "Government Assistant":"nav.government",
    "Voice Commands":      "nav.voice",
    "Settings":            "nav.settings",
    "View Code":           "nav.code",
}


def _track_language_switched() -> None:
    """on_change callback for the Hinglish mode toggle; fires a Pendo track event."""
    pendo.track(
        "language_switched",
        properties={"lang_is_hinglish": st.session_state.get("lang_is_hinglish", False)},
    )


def render_sidebar() -> str:
    """Render product navigation and return the selected page name."""

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-brand">
              <span class="brand-mark">A</span><span class="brand-name">Aster Ops</span>
              <div class="brand-caption">{t("sidebar.caption")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_byok_section()

        # ── Resolve pending navigation BEFORE the radio is instantiated ──────
        # Streamlit forbids writing a widget-keyed session-state key after the
        # widget has rendered.  Every in-page navigation button therefore sets
        # "_nav_pending" instead, and we flush it here so the radio always
        # starts the run with the correct value already committed.
        if _pending := st.session_state.pop("_nav_pending", None):
            if _pending in _NAV_KEYS:
                st.session_state["nav_selected_page"] = _pending

        selected = st.radio(
            "Navigation",
            options=list(_NAV_KEYS),
            format_func=lambda page: t(_NAV_KEYS[page]),
            label_visibility="collapsed",
            key="nav_selected_page",
        )

        # ── Language toggle ──────────────────────────────────────────────
        st.markdown(
            "<div style='margin-top:1rem; padding-top:0.75rem; "
            "border-top:1px solid rgba(217,247,231,.13);'></div>",
            unsafe_allow_html=True,
        )
        st.toggle(
            t("sidebar.lang.toggle"),
            key="lang_is_hinglish",
            on_change=_track_language_switched,
        )

        st.markdown(
            f"""
            <div class="sidebar-note">
              <strong>{t("sidebar.note.heading")}</strong><br>
              {t("sidebar.note.body")}
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
