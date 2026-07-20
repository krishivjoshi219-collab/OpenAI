"""Voice-driven AI operations assistant page.

Lets the user speak business commands in English or Hindi.  The audio is
transcribed by Groq Whisper, then executed through the business AI service
(tool-calling against the active workspace).
"""

from __future__ import annotations

from uuid import UUID

import streamlit as st

from app.ai.client import create_business_ai_service
from app.business.engine import BusinessEngine
from app.database.session import create_session_factory, session_scope
from app.models import Business
from app.services.dashboard import DashboardService
from app.i18n import t
from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.voice_input import render_voice_input

_EXAMPLES_EN = [
    "Create a customer named Priya Sharma, email priya@example.com",
    "Add a product called Organic Cotton Tote, price 450, SKU TOTE-001",
    "Create an invoice for Priya Sharma for 3 Organic Cotton Totes",
    "Set the stock for SKU TOTE-001 to 120 units",
    "Remind me to follow up with Priya on Friday",
    "Search for customers named Sharma",
]

_EXAMPLES_HI = [
    "Priya Sharma के लिए एक customer बनाओ, email priya@example.com",
    "Organic Cotton Tote का invoice बनाओ ₹450 में",
    "SKU TOTE-001 की stock 120 units करो",
    "शुक्रवार को Priya को follow up reminder बनाओ",
]


def render() -> None:
    """Render the voice AI command workspace."""

    render_page_header(
        t("voice.eyebrow"),
        t("voice.title"),
        t("voice.subtitle"),
    )

    st.session_state.setdefault("voice_history", [])
    st.session_state.setdefault("voice_conversation", None)

    try:
        with session_scope(create_session_factory()) as session:
            businesses: list[Business] = DashboardService(session).list_businesses()
    except Exception as error:
        st.error(f"Could not load workspaces: {error}")
        return

    if not businesses:
        _render_no_workspace()
        return

    business_id = _select_workspace(businesses)

    st.write("")
    left_col, right_col = st.columns([1.6, 1], gap="large")

    with left_col:
        render_section_title("Voice input")
        transcript = render_voice_input(
            key="voice_cmd",
            label="🎙 Record your command",
            help_text='Supports English and Hindi · e.g. "Create an invoice for Acme Corp for $500"',
        )

        if transcript:
            st.write("")
            if st.button(
                "▶ Run command",
                type="primary",
                key="run_voice_cmd",
                width="stretch",
            ):
                _run_command(transcript, business_id)

        history: list[dict] = st.session_state.get("voice_history", [])
        if history:
            st.write("")
            render_section_title("Command history")
            for entry in reversed(history):
                _render_history_entry(entry)

    with right_col:
        _render_examples()


def _render_no_workspace() -> None:
    """Prompt the user to complete onboarding before using voice commands."""
    st.write("")
    st.info(
        "Complete onboarding to enable voice commands. "
        "Head to **Onboarding** in the sidebar to create your business workspace."
    )
    st.markdown(
        """
        <div class="product-card" style="margin-top:1rem;">
          <div class="eyebrow">Get started</div>
          <div class="row-primary" style="margin-bottom:.4rem;">Create your workspace first</div>
          <div class="row-secondary">Once your business is set up you can come back here and
          speak commands like "Create an invoice for ₹5,000" or "Add a new customer".</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    if st.button("Go to Onboarding", type="primary", width="stretch"):
        st.session_state["_nav_pending"] = "Onboarding"
        st.rerun()



def _select_workspace(businesses: list[Business]) -> UUID:
    """Return the selected business UUID, defaulting to the onboarding workspace."""
    ids = [b.id for b in businesses]
    current = st.session_state.get("onboarding_business_id")
    try:
        onboarding_id = UUID(current) if isinstance(current, str) else None
    except ValueError:
        onboarding_id = None
    default_index = ids.index(onboarding_id) if onboarding_id in ids else 0
    selected = st.selectbox(
        "Workspace",
        businesses,
        index=default_index,
        format_func=lambda b: b.name,
        label_visibility="collapsed",
        key="voice_workspace",
    )
    return selected.id  # type: ignore[return-value]


def _run_command(command: str, business_id: UUID) -> None:
    """Execute a transcribed command through the business AI service."""
    entry: dict
    with st.spinner("Working on it…"):
        try:
            with session_scope(create_session_factory()) as session:
                engine = BusinessEngine(session)
                ai_service = create_business_ai_service(engine, business_id)
                conversation = st.session_state.get("voice_conversation")
                result = ai_service.business_command(command, conversation=conversation)
            st.session_state["voice_conversation"] = result.conversation

            structured = result.structured_output or {}
            entry = {
                "command": command,
                "summary": structured.get("summary", ""),
                "outcome": structured.get("outcome", ""),
                "next_steps": structured.get("next_steps", []),
                "actions": result.actions,
                "error": None,
            }
            if structured.get("summary"):
                st.success(structured["summary"])
            if structured.get("outcome"):
                st.write(structured["outcome"])
            for step in structured.get("next_steps", []):
                st.info(f"→ {step}")

        except Exception as exc:
            entry = {
                "command": command,
                "summary": None,
                "outcome": None,
                "next_steps": [],
                "actions": [],
                "error": str(exc),
            }
            st.error(f"Command failed: {exc}")

    history: list[dict] = st.session_state.get("voice_history", [])
    history.append(entry)
    st.session_state["voice_history"] = history


def _render_history_entry(entry: dict) -> None:
    """Render a single command history card."""
    with st.container(border=True):
        st.markdown(
            f'<div class="row-primary">🎙 {entry["command"]}</div>',
            unsafe_allow_html=True,
        )
        if entry.get("error"):
            st.error(entry["error"])
        else:
            if entry.get("summary"):
                st.caption(entry["summary"])
            for action in entry.get("actions", ()):
                icon = "✓" if getattr(action, "status", "") == "completed" else "✗"
                tool = getattr(action, "tool_name", "")
                reason = getattr(action, "reason", "")
                st.caption(f"{icon} `{tool}` — {reason}")


def _render_examples() -> None:
    """Render example commands panel."""
    render_section_title("Example commands")
    st.markdown('<div class="voice-examples">', unsafe_allow_html=True)
    st.markdown(
        '<div class="voice-example-lang">English 🇬🇧</div>',
        unsafe_allow_html=True,
    )
    for ex in _EXAMPLES_EN:
        st.markdown(
            f'<div class="voice-example-chip">"{ex}"</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="voice-example-lang" style="margin-top:.85rem;">Hindi 🇮🇳</div>',
        unsafe_allow_html=True,
    )
    for ex in _EXAMPLES_HI:
        st.markdown(
            f'<div class="voice-example-chip">"{ex}"</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
