"""Tests for conservative, jurisdiction-specific government guidance."""

from app.services.government import (
    GovernmentAssistantService,
    GovernmentGuidanceRequest,
    Jurisdiction,
)


def test_india_guidance_has_gst_udyam_documents_and_uncertainty() -> None:
    """India output is structured, sourced, and does not make legal determinations."""

    guidance = GovernmentAssistantService().generate_guidance(
        GovernmentGuidanceRequest(
            jurisdiction=Jurisdiction.INDIA,
            location="Karnataka",
            has_employees=True,
        )
    )

    assert any("GST" in item.title for item in guidance.checklist)
    assert any("Udyam" in item.title for item in guidance.checklist)
    assert any("employer" in item.title.lower() for item in guidance.checklist)
    assert any("GST" in item.title for item in guidance.required_documents)
    assert "not legal, tax, or accounting advice" in guidance.disclaimer
    assert all(source.url.startswith("https://") for source in guidance.official_sources)


def test_united_states_guidance_adapts_to_sales_and_employees() -> None:
    """U.S. guidance adds fact-dependent tax and employer review steps."""

    guidance = GovernmentAssistantService().generate_guidance(
        GovernmentGuidanceRequest(
            jurisdiction=Jurisdiction.UNITED_STATES,
            business_structure="LLC",
            location="California",
            has_employees=True,
            sells_goods_or_services=True,
        )
    )

    assert any("EIN" in item.detail for item in guidance.checklist)
    assert any("sales-tax" in item.title.lower() for item in guidance.checklist)
    assert any("employer" in item.title.lower() for item in guidance.checklist)
    assert "state-specific" in guidance.business_registration_guidance
    assert len(guidance.uncertainties) >= 3
