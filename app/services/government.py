"""Conservative, source-linked government registration guidance."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Jurisdiction(StrEnum):
    """Jurisdictions currently covered by the government assistant."""

    INDIA = "india"
    UNITED_STATES = "united_states"


@dataclass(frozen=True)
class GovernmentGuidanceRequest:
    """User-provided facts used to scope informational guidance."""

    jurisdiction: Jurisdiction
    business_structure: str | None = None
    location: str | None = None
    has_employees: bool = False
    sells_goods_or_services: bool = False


@dataclass(frozen=True)
class GuidanceItem:
    """One checkable informational step or document."""

    title: str
    detail: str


@dataclass(frozen=True)
class OfficialSource:
    """A first-party source the user should check before acting."""

    label: str
    url: str


@dataclass(frozen=True)
class GovernmentGuidance:
    """Structured, non-legal guidance returned by the assistant."""

    jurisdiction: Jurisdiction
    checklist: tuple[GuidanceItem, ...]
    required_documents: tuple[GuidanceItem, ...]
    business_registration_guidance: str
    tax_registration_guidance: str
    uncertainties: tuple[str, ...]
    disclaimer: str
    official_sources: tuple[OfficialSource, ...]


class GovernmentAssistantService:
    """Generate conservative country-specific registration and tax preparation guidance."""

    _DISCLAIMER = (
        "This is general educational information, not legal, tax, or accounting advice. "
        "Rules, thresholds, forms, fees, and deadlines can change. Confirm your facts with the "
        "relevant government authority and a qualified local professional before filing or acting."
    )

    def generate_guidance(self, request: GovernmentGuidanceRequest) -> GovernmentGuidance:
        """Return country-specific preparation steps without deciding legal obligations."""

        if request.jurisdiction is Jurisdiction.INDIA:
            return self._india(request)
        if request.jurisdiction is Jurisdiction.UNITED_STATES:
            return self._united_states(request)
        raise ValueError(f"Unsupported jurisdiction: {request.jurisdiction}")

    def _india(self, request: GovernmentGuidanceRequest) -> GovernmentGuidance:
        checklist = [
            GuidanceItem(
                "Choose and validate the business structure",
                "Compare proprietorship, partnership, LLP, and company options with a qualified Indian professional; the appropriate path depends on ownership, liability, funding, and state facts.",
            ),
            GuidanceItem(
                "Confirm the registration route",
                "For a company or LLP, review the current Ministry of Corporate Affairs incorporation process. Also check state and local registrations, licences, and labour requirements that may apply.",
            ),
            GuidanceItem(
                "Assess Udyam registration",
                "If the enterprise may qualify as an MSME, review Udyam eligibility and registration on the official portal. Do not use a private portal claiming to be the government service.",
            ),
            GuidanceItem(
                "Assess GST registration",
                "Check GST registration applicability using your state, turnover, supplies, and business model. Registration is not assumed merely because a business exists.",
            ),
        ]
        if request.has_employees:
            checklist.append(
                GuidanceItem(
                    "Review employer registrations",
                    "Employment can trigger additional central and state obligations. Verify current EPFO, ESIC, professional-tax, labour, and payroll requirements for your facts.",
                )
            )
        documents = (
            GuidanceItem(
                "Identity and tax identifiers",
                "Keep PAN and the relevant promoters’/proprietor’s identification details ready. Aadhaar, PAN, and GST-linked information may be relevant to Udyam, subject to the current portal rules.",
            ),
            GuidanceItem(
                "Business constitution evidence",
                "Prepare the applicable deed, incorporation/registration records, ownership or director details, and authorisations for the chosen structure.",
            ),
            GuidanceItem(
                "Principal-place-of-business evidence",
                "Keep current ownership, lease, consent, or utility evidence for the registered/principal address if the applicable registration asks for it.",
            ),
            GuidanceItem(
                "GST preparation documents",
                "The official GST checklist covers documents that can vary by entity and address arrangement, including constitution, authorised-signatory, address, and bank details. Verify the current list before upload.",
            ),
        )
        location = request.location or "your state/Union Territory"
        structure = request.business_structure or "your proposed structure"
        return GovernmentGuidance(
            jurisdiction=Jurisdiction.INDIA,
            checklist=tuple(checklist),
            required_documents=documents,
            business_registration_guidance=(
                f"For {structure} in {location}, start by confirming the correct entity and registration route. "
                "Company/LLP incorporation is handled through MCA processes; sole proprietorships and other structures can have different proof, local-registration, and sector-licence requirements."
            ),
            tax_registration_guidance=(
                "GST registration depends on facts such as place of supply, turnover, type of supply, and other statutory rules. "
                "Use the official GST portal and confirm income-tax, payroll, and state/local tax obligations separately."
            ),
            uncertainties=(
                "The applicable entity form cannot be determined from this information.",
                "State, municipal, sector-specific, and employment obligations may add steps or documents.",
                "GST applicability and thresholds are fact-dependent and must be checked against current official rules.",
            ),
            disclaimer=self._DISCLAIMER,
            official_sources=(
                OfficialSource(
                    "MCA SPICe+ incorporation FAQs",
                    "https://www.mca.gov.in/Ministry/pdf/SpicePlusFAQS_12032021.pdf",
                ),
                OfficialSource(
                    "GST registration document checklist",
                    "https://tutorial.gst.gov.in/cbt/registration/gstregistration/course/story.html",
                ),
                OfficialSource("Udyam Registration portal", "https://udyamregistration.gov.in/"),
                OfficialSource("National Single Window System", "https://www.nsws.gov.in/"),
            ),
        )

    def _united_states(self, request: GovernmentGuidanceRequest) -> GovernmentGuidance:
        checklist = [
            GuidanceItem(
                "Choose a structure and state of formation",
                "Compare sole proprietorship, partnership, LLC, corporation, and other options with a qualified U.S. attorney or tax professional. State law and ownership facts matter.",
            ),
            GuidanceItem(
                "Register with the appropriate state authority if required",
                "LLCs, corporations, partnerships, and nonprofits commonly register with the state. Check the Secretary of State or equivalent agency where the business operates.",
            ),
            GuidanceItem(
                "Confirm local licences and permits",
                "Cities, counties, and industry regulators can require separate registrations, licences, or trade-name filings.",
            ),
            GuidanceItem(
                "Apply for an EIN only after legal formation when applicable",
                "The IRS says an EIN is a federal tax ID. Whether you need one depends on the entity and tax facts; obtain it directly from the IRS rather than a paid intermediary.",
            ),
        ]
        if request.sells_goods_or_services:
            checklist.append(
                GuidanceItem(
                    "Check state sales-tax registration",
                    "Sales/use-tax registration and collection rules are state-specific and may depend on products, services, customer location, and nexus. Check the relevant state revenue authority.",
                )
            )
        if request.has_employees:
            checklist.append(
                GuidanceItem(
                    "Check employer tax and payroll registrations",
                    "Employers may have federal, state, and local withholding, unemployment, and payroll obligations. Confirm registration and filing requirements before payroll begins.",
                )
            )
        documents = (
            GuidanceItem(
                "Formation information",
                "Prepare the legal business name, principal address, ownership/management details, and the information required by your chosen state filing.",
            ),
            GuidanceItem(
                "Registered-agent details",
                "An LLC, corporation, partnership, or nonprofit may need a registered agent before state filing; confirm the state’s current rule.",
            ),
            GuidanceItem(
                "State formation records",
                "Keep stamped/accepted formation documents, operating agreement or bylaws where appropriate, and state correspondence.",
            ),
            GuidanceItem(
                "Federal tax preparation",
                "For an EIN application, prepare the responsible party and entity information required by the IRS. Do not share sensitive identifiers except directly through trusted official processes.",
            ),
        )
        location = request.location or "your state and locality"
        structure = request.business_structure or "your proposed structure"
        return GovernmentGuidance(
            jurisdiction=Jurisdiction.UNITED_STATES,
            checklist=tuple(checklist),
            required_documents=documents,
            business_registration_guidance=(
                f"For {structure} in {location}, registration depends primarily on structure and where you conduct business. "
                "Use the SBA’s state-specific guidance and the relevant state agency rather than assuming one national incorporation process."
            ),
            tax_registration_guidance=(
                "Federal tax treatment depends on the entity and elections; the IRS describes EIN, business, estimated, and employment-tax paths. "
                "State income, franchise, sales/use, and payroll registrations are separate and vary by jurisdiction."
            ),
            uncertainties=(
                "State, county, city, and industry requirements can differ substantially.",
                "An EIN, federal tax treatment, and state tax registration cannot be determined without the entity, ownership, activity, and location facts.",
                "Sales-tax nexus and employer obligations need current jurisdiction-specific confirmation.",
            ),
            disclaimer=self._DISCLAIMER,
            official_sources=(
                OfficialSource(
                    "SBA: Register your business",
                    "https://www.sba.gov/business-guide/launch-your-business/register-your-business",
                ),
                OfficialSource(
                    "IRS: Employer Identification Number",
                    "https://www.irs.gov/businesses/employer-identification-number",
                ),
                OfficialSource(
                    "IRS: Starting a business",
                    "https://www.irs.gov/businesses/small-businesses-self-employed/starting-a-business",
                ),
                OfficialSource(
                    "IRS: Filing and paying business taxes",
                    "https://www.irs.gov/businesses/small-businesses-self-employed/filing-and-paying-your-business-taxes",
                ),
            ),
        )
