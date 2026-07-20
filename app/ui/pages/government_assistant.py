"""Streamlit workspace for conservative India and U.S. government guidance."""

# ruff: noqa: E501

from __future__ import annotations

import streamlit as st

from app import pendo
from app.services.government import (
    GovernmentAssistantService,
    GovernmentGuidance,
    GovernmentGuidanceRequest,
    Jurisdiction,
)
from app.i18n import t
from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.voice_input import render_voice_input


def render() -> None:
    """Render government-registration guidance with prominent limitations."""

    st.session_state.setdefault("government_guidance_result", None)

    render_page_header(
        t("gov.eyebrow"),
        t("gov.title"),
        t("gov.subtitle"),
    )
    st.warning(
        "This tool provides general educational information only. Verify every requirement with the relevant authority and a qualified local professional before filing."
    )

    # ── Voice pre-fill ────────────────────────────────────────────────────
    with st.expander("🎙 Fill form fields by voice", expanded=False):
        gov_transcript = render_voice_input(
            key="gov_voice",
            label="Record to fill a form field",
            help_text="Record once, then choose which field to populate.",
        )
        if gov_transcript:
            st.markdown(
                '<div class="voice-fill-hint">Choose a field to fill with the transcription above:</div>',
                unsafe_allow_html=True,
            )
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("→ Use as business structure", key="gov_fill_structure", width="stretch"):
                    st.session_state["gov_structure_input"] = gov_transcript
                    st.rerun()
            with col_b:
                if st.button("→ Use as location", key="gov_fill_location", width="stretch"):
                    st.session_state["gov_location_input"] = gov_transcript
                    st.rerun()

    # ── Guidance form ─────────────────────────────────────────────────────
    with st.form("government_guidance_form"):
        jurisdiction = Jurisdiction(
            st.selectbox(
                "Country",
                options=[Jurisdiction.INDIA, Jurisdiction.UNITED_STATES],
                format_func=lambda value: (
                    "India" if value is Jurisdiction.INDIA else "United States"
                ),
            )
        )
        left, right = st.columns(2)
        with left:
            structure = st.text_input(
                "Proposed business structure",
                placeholder="e.g. LLC, partnership, proprietorship",
                key="gov_structure_input",
            )
        with right:
            location = st.text_input(
                "State / Union Territory / locality",
                placeholder="e.g. Karnataka or California",
                key="gov_location_input",
            )
        employees, sales = st.columns(2)
        with employees:
            has_employees = st.checkbox("I expect to have employees")
        with sales:
            sells_goods_or_services = st.checkbox("I will sell goods or services")
        submitted = st.form_submit_button("Generate preparation checklist", type="primary")
    if submitted:
        try:
            guidance = GovernmentAssistantService().generate_guidance(
                GovernmentGuidanceRequest(
                    jurisdiction=jurisdiction,
                    business_structure=structure or None,
                    location=location or None,
                    has_employees=has_employees,
                    sells_goods_or_services=sells_goods_or_services,
                )
            )
            st.session_state["government_guidance_result"] = guidance
            pendo.track(
                "government_guidance_generated",
                properties={
                    "jurisdiction": jurisdiction.value,
                    "business_structure": structure or "",
                    "location": location or "",
                    "has_employees": has_employees,
                    "sells_goods_or_services": sells_goods_or_services,
                    "checklist_item_count": len(guidance.checklist),
                    "required_document_count": len(
                        guidance.required_documents
                    ),
                    "official_source_count": len(
                        guidance.official_sources
                    ),
                },
            )
        except Exception as exc:
            _render_fallback_guidance(jurisdiction, structure, location, str(exc))
    guidance = st.session_state.get("government_guidance_result")
    if isinstance(guidance, GovernmentGuidance):
        _render_guidance(guidance)


def _render_fallback_guidance(
    jurisdiction: Jurisdiction,
    structure: str | None,
    location: str | None,
    error: str,
) -> None:
    """Render structural fallback text when guidance generation fails."""

    render_section_title("Preparation checklist")
    st.warning(
        f"Could not load live guidance right now ({error}). "
        "Showing general structural steps instead."
    )
    structure = structure or "your proposed structure"
    location = location or "your state / locality"
    if jurisdiction is Jurisdiction.INDIA:
        st.markdown(
            f"**1. Choose and validate the business structure**\n\n"
            f"Compare proprietorship, partnership, LLP, and company options for {structure} in {location}."
        )
        st.markdown(
            "**2. Confirm the registration route**\n\n"
            "Review the current MCA incorporation process and any state/local registrations."
        )
        st.markdown(
            "**3. Assess Udyam and GST registration**\n\n"
            "Check Udyam eligibility and GST applicability based on turnover and business model."
        )
    else:
        st.markdown(
            f"**1. Choose a structure and state of formation**\n\n"
            f"Compare LLC, corporation, partnership, and other options for {structure} in {location}."
        )
        st.markdown(
            "**2. Register with the appropriate state authority**\n\n"
            "Check the Secretary of State or equivalent agency where the business operates."
        )
        st.markdown(
            "**3. Confirm local licences, permits, and federal tax steps**\n\n"
            "Cities, counties, and industry regulators can require separate registrations."
        )


def _render_guidance(guidance: GovernmentGuidance) -> None:
    """Render generated guidance in a clear, scannable structure."""

    render_section_title("Preparation checklist")
    for index, item in enumerate(guidance.checklist, start=1):
        with st.container(border=True):
            st.markdown(f"**{index}. {item.title}**")
            st.write(item.detail)
    left, right = st.columns(2, gap="large")
    with left:
        render_section_title("Business registration guidance")
        with st.container(border=True):
            st.write(guidance.business_registration_guidance)
        render_section_title("Tax registration guidance")
        with st.container(border=True):
            st.write(guidance.tax_registration_guidance)
    with right:
        render_section_title("Documents to prepare")
        with st.container(border=True):
            for item in guidance.required_documents:
                st.markdown(f"**{item.title}**")
                st.caption(item.detail)
                st.divider()
    render_section_title("What remains uncertain")
    for uncertainty in guidance.uncertainties:
        st.info(uncertainty)
    render_section_title("Verify with official sources")
    source_columns = st.columns(min(len(guidance.official_sources), 2))
    for index, source in enumerate(guidance.official_sources):
        with source_columns[index % len(source_columns)]:
            st.link_button(source.label, source.url, width="stretch")
    st.caption(guidance.disclaimer)
