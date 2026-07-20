"""Bring Your Own Key (BYOK) sidebar configuration."""

from __future__ import annotations

import streamlit as st
from config.settings import get_settings


# ---------------------------------------------------------------------------
# Module-level dialog — @st.dialog must NOT be defined inside another function
# or a conditional block.  The title is a static string (decorator constraint);
# body text is translated dynamically via t() at call time.
# ---------------------------------------------------------------------------


@st.dialog("Add Your API Key / Apni API Key Daalo")
def _show_key_dialog() -> None:
    """Prompt the user for an API key and save it to the BYOK session keys."""
    from app.i18n import t  # local import avoids circular dependency at module load

    settings = get_settings()
    provider = settings.ai_provider.lower()

    st.markdown(f"**{t('byok.dialog.prompt')}**")

    if provider == "openai":
        st.text_input("OpenAI API Key", type="password", key="dlg_openai")
    elif provider == "groq":
        st.text_input("Groq API Key", type="password", key="dlg_groq")
    elif provider == "gemini":
        st.text_input("Gemini API Key", type="password", key="dlg_gemini")

    if st.button(t("byok.btn.save"), type="primary"):
        # Copy the dialog value into the BYOK session-state keys that
        # _get_sidebar_key() in client.py reads on every AI call.
        if provider == "openai":
            value = st.session_state.get("dlg_openai", "")
            if value:
                st.session_state["byok_openai_api_key"] = value
        elif provider == "groq":
            value = st.session_state.get("dlg_groq", "")
            if value:
                st.session_state["byok_groq_api_key"] = value
        elif provider == "gemini":
            value = st.session_state.get("dlg_gemini", "")
            if value:
                st.session_state["byok_gemini_api_key"] = value
        st.rerun()


def render_byok_section() -> None:
    """Render masked API key inputs in the sidebar with validation."""
    from app.i18n import t  # local import avoids circular dependency at module load

    st.markdown(
        f"""
        <div style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid rgba(217,247,231,.13);">
          <div class="eyebrow" style="color:#c7f36b;">{t("byok.heading")}</div>
          <div style="color:#9bb7aa; font-size:.72rem; margin-bottom:.6rem; line-height:1.4;">
            {t("byok.caption")}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.text_input(
        "OpenAI API Key",
        type="password",
        key="byok_openai_api_key",
        placeholder="sk-...",
        label_visibility="collapsed",
    )
    st.text_input(
        "Groq API Key",
        type="password",
        key="byok_groq_api_key",
        placeholder="gsk_...",
        label_visibility="collapsed",
    )
    st.text_input(
        "Gemini API Key",
        type="password",
        key="byok_gemini_api_key",
        placeholder="AIza...",
        label_visibility="collapsed",
    )

    _show_warning_if_needed()


def _show_warning_if_needed() -> None:
    """Show warning callout and open the key dialog when primary keys are missing or preflight failed."""
    from app.i18n import t  # local import avoids circular dependency at module load

    settings = get_settings()
    provider = settings.ai_provider.lower()

    has_sidebar_key = False
    primary_missing = False
    preflight_failed = False

    if provider == "openai":
        has_sidebar_key = bool(st.session_state.get("byok_openai_api_key"))
        primary_missing = not settings.openai_api_key and not has_sidebar_key
        preflight_failed = bool(st.session_state.get("preflight_failed_openai"))
    elif provider == "groq":
        has_sidebar_key = bool(st.session_state.get("byok_groq_api_key"))
        primary_missing = not settings.groq_api_key and not has_sidebar_key
        preflight_failed = bool(st.session_state.get("preflight_failed_groq"))
    elif provider == "gemini":
        has_sidebar_key = bool(st.session_state.get("byok_gemini_api_key"))
        primary_missing = not settings.gemini_api_key and not has_sidebar_key
        preflight_failed = bool(st.session_state.get("preflight_failed_gemini"))

    rate_limited = bool(st.session_state.get("byok_rate_limit_error", False))
    if rate_limited and has_sidebar_key:
        rate_limited = False

    if primary_missing or rate_limited or preflight_failed:
        if rate_limited:
            st.session_state["byok_rate_limit_error"] = False

        st.error(t("byok.error"))
        _show_key_dialog()
