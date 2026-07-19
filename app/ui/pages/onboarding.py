"""Guided onboarding flow for business setup and reviewed data imports."""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

import streamlit as st

from app import pendo
from app.database.session import create_session_factory, session_scope
from app.onboarding.extraction import ExtractionPreview, ImportKind, create_extraction_registry
from app.onboarding.service import ImportConfirmation, OnboardingImportService
from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.voice_input import render_voice_input


def render() -> None:
    """Render setup, extraction review, and confirmation states."""

    _initialize_state()
    render_page_header(
        "Workspace setup",
        "Let’s make this feel like your business.",
        "Create your business workspace, then review exactly what will be imported before anything "
        "is saved.",
    )
    if _business_id() is None:
        _render_business_profile()
        return
    _render_import_flow()


def _initialize_state() -> None:
    """Set default UI-only state for a Streamlit session."""

    st.session_state.setdefault("onboarding_business_id", None)
    st.session_state.setdefault("onboarding_preview", None)
    st.session_state.setdefault("onboarding_confirmation", None)
    st.session_state.setdefault("onboarding_step", 2)


def _business_id() -> UUID | None:
    """Return the persisted business identifier for this onboarding session."""

    value = st.session_state["onboarding_business_id"]
    return UUID(value) if isinstance(value, str) else None


def _render_business_profile() -> None:
    """Render and persist the first onboarding step."""

    st.progress(25, text="Step 1 of 4 · Create your business workspace")
    render_section_title("Business profile")

    # ── Voice pre-fill for business name ─────────────────────────────────
    with st.expander("🎙 Say your business name instead of typing", expanded=False):
        obrd_transcript = render_voice_input(
            key="obrd_voice",
            label="Record your business name",
            help_text="Speak your business name in English or Hindi, then click the button below.",
        )
        if obrd_transcript:
            if st.button(
                "→ Use as business name",
                key="obrd_fill_name",
                width="content",
            ):
                st.session_state["obrd_biz_name"] = obrd_transcript
                st.rerun()

    with st.form("business_profile"):
        left, right = st.columns(2, gap="large")
        with left:
            name = st.text_input(
                "Business name",
                placeholder="e.g. Northstar Studio",
                key="obrd_biz_name",
            )
            email = st.text_input("Primary contact email", placeholder="you@company.com")
        with right:
            currency = st.selectbox("Operating currency", ["USD", "EUR", "INR"])
            st.selectbox("Team size", ["Just me", "2–10 people", "11–50 people", "51+ people"])
        submitted = st.form_submit_button("Create workspace", type="primary")
    if submitted:
        if not name.strip():
            st.error("Enter a business name to continue.")
            return
        try:
            with session_scope(create_session_factory()) as session:
                business = OnboardingImportService(session).create_business(name, email, currency)
            st.session_state["onboarding_business_id"] = str(business.id)
            pendo.track(
                "business_workspace_created",
                account_id=str(business.id),
                properties={
                    "business_id": str(business.id),
                    "business_name": name.strip(),
                    "currency_code": currency,
                    "has_email": bool(email and email.strip()),
                },
            )
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except Exception as exc:
            error_str = str(exc)
            if "no such table" in error_str and "business" in error_str.lower():
                try:
                    from app.database.session import create_all_tables
                    create_all_tables()
                    st.rerun()
                except Exception as db_error:
                    st.error(f"Database initialization failed: {db_error}")
            else:
                st.error(f"Failed to create workspace: {exc}")


def _render_import_flow() -> None:
    """Render preview and explicit confirmation controls for onboarding imports."""

    current_step = st.session_state.get("onboarding_step", 2)
    if current_step == 2:
        st.progress(50, text="Step 2 of 4 · Import your operational data")
        st.success("Business workspace created. Your imports will remain scoped to this business.")
        render_section_title("Choose data to import")
        kind = ImportKind(
            st.selectbox(
                "Import type",
                options=[kind.value for kind in ImportKind],
                format_func=_import_label,
            )
        )
        uploaded_file = st.file_uploader(
            "Upload a file",
            type=["csv", "xlsx", "pdf"],
            help="CSV and PDF are supported. XLSX support is planned.",
        )
        if uploaded_file is not None and st.button("Review extracted information", type="primary"):
            _create_preview(kind, uploaded_file.name, uploaded_file.getvalue())
        preview = st.session_state["onboarding_preview"]
        if isinstance(preview, ExtractionPreview):
            _render_preview(preview)
    elif current_step == 3:
        st.progress(75, text="Step 3 of 4 · Data imported and ready to review")
        st.success("Your operational data has been imported and is ready for review.")
        confirmation = st.session_state.get("onboarding_confirmation")
        if isinstance(confirmation, ImportConfirmation):
            st.success(
                f"Import complete: {confirmation.created} created, {confirmation.updated} updated, "
                f"{confirmation.skipped} skipped."
            )
            for message in confirmation.messages:
                st.info(message)
            if st.button("Import another file"):
                st.session_state["onboarding_confirmation"] = None
                st.session_state["onboarding_step"] = 2
                st.session_state["onboarding_preview"] = None
                st.rerun()
        else:
            if st.button("← Back to import"):
                st.session_state["onboarding_step"] = 2
                st.rerun()


def _create_preview(kind: ImportKind, file_name: str, content: bytes) -> None:
    """Extract a file into an in-memory review result without persistence."""

    try:
        preview = create_extraction_registry().extract(
            kind, file_name, content
        )
        st.session_state["onboarding_preview"] = preview
        st.session_state["onboarding_confirmation"] = None
        bid = _business_id()
        extension = (
            file_name.rsplit(".", maxsplit=1)[-1] if "." in file_name else ""
        )
        pendo.track(
            "onboarding_file_extracted",
            account_id=str(bid) if bid else "system",
            properties={
                "import_kind": kind.value,
                "file_name": file_name,
                "file_extension": extension,
                "record_count": len(preview.records),
                "is_supported": preview.is_supported,
                "warning_count": len(preview.warnings),
            },
        )
    except Exception as error:
        st.error(f"We could not read that file: {error}")


def _to_safe_records(records: list[dict[str, object]]) -> list[dict[str, str | float | int | bool | None]]:
    safe: list[dict[str, str | float | int | bool | None]] = []
    for record in records:
        row: dict[str, str | float | int | bool | None] = {}
        for key, value in record.items():
            if value is None:
                row[key] = None
            elif hasattr(value, "isoformat"):
                row[key] = value.isoformat()
            elif isinstance(value, (int, float, bool)):
                row[key] = value
            else:
                row[key] = str(value)
        safe.append(row)
    return safe


def _render_preview(preview: ExtractionPreview) -> None:
    """Render the confirmation screen for a non-persisted extraction result."""

    render_section_title("Review before import")
    if preview.warnings:
        for warning in preview.warnings:
            st.warning(warning)
    records = [asdict(record) for record in preview.records] if preview.records else []
    if records:
        if "customer_name" not in records[0]:
            for row in records:
                row.setdefault("customer_name", "Default Customer")
        safe_records = _to_safe_records(records)
        try:
            edited = st.data_editor(
                safe_records,
                num_rows="dynamic",
                width="stretch",
                key="onboarding_preview_editor",
            )
        except Exception as exc:
            st.error(f"Preview render failed: {exc}")
            edited = safe_records
        col_confirm, col_proceed, col_discard = st.columns([1, 1, 2])
        with col_confirm:
            if st.button("Confirm import", type="primary", width="stretch"):
                _confirm_preview(preview)
        with col_proceed:
            if st.button("Confirm & Proceed to Next Step", width="stretch"):
                if "onboarding_step" in st.session_state:
                    st.session_state.onboarding_step = 3
                elif "step" in st.session_state:
                    st.session_state.step = 3
                st.session_state.onboarding_preview = None
                st.rerun()
        with col_discard:
            if st.button("Discard preview", width="stretch"):
                st.session_state["onboarding_preview"] = None
                st.rerun()
    else:
        st.info("No rows were found in this file. Nothing will be saved.")
        if st.button("Confirm & Proceed to Next Step", type="primary", width="stretch"):
            if "onboarding_step" in st.session_state:
                st.session_state.onboarding_step = 3
            elif "step" in st.session_state:
                st.session_state.step = 3
            st.session_state.onboarding_preview = None
            st.rerun()


def _confirm_preview(preview: ExtractionPreview) -> None:
    """Persist a reviewed preview in one database transaction."""

    business_id = _business_id()
    if business_id is None:
        st.error("Create a business workspace before confirming an import.")
        return
    try:
        with session_scope(create_session_factory()) as session:
            confirmation = OnboardingImportService(session).confirm(business_id, preview)
        st.session_state["onboarding_confirmation"] = confirmation
        st.session_state["onboarding_preview"] = None
        st.session_state["onboarding_step"] = 3
        pendo.track(
            "onboarding_import_confirmed",
            account_id=str(business_id),
            properties={
                "business_id": str(business_id),
                "import_kind": preview.kind.value,
                "file_name": preview.file_name,
                "records_created": confirmation.created,
                "records_updated": confirmation.updated,
                "records_skipped": confirmation.skipped,
                "message_count": len(confirmation.messages),
            },
        )
        st.rerun()
    except Exception as error:
        st.error(f"Import failed: {error}")


def _import_label(value: str) -> str:
    """Provide concise human-readable labels for import type options."""

    labels = {
        ImportKind.INVOICES.value: "Invoices",
        ImportKind.CUSTOMERS.value: "Customer list",
        ImportKind.PRODUCTS.value: "Product list",
        ImportKind.STOCK.value: "Stock sheet",
    }
    return labels[value]
