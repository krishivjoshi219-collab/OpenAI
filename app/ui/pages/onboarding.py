"""Guided onboarding flow — business setup and AI-powered data import."""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

import streamlit as st

from app.i18n import t

from app import pendo
from app.database.session import create_session_factory, session_scope
from app.onboarding.extraction import (
    ExtractionPreview,
    ImportKind,
    create_extraction_registry,
)
from app.onboarding.service import ImportConfirmation, OnboardingImportService
from app.ui.components.layout import render_page_header, render_section_title
from app.ui.components.voice_input import render_voice_input

# ── labels shown in the UI for each import kind ───────────────────────────────

_KIND_LABELS: dict[str, str] = {
    ImportKind.INVOICES.value:  "📄 Invoices",
    ImportKind.CUSTOMERS.value: "👥 Customer list",
    ImportKind.PRODUCTS.value:  "📦 Product catalogue",
    ImportKind.STOCK.value:     "🏭 Stock / inventory",
}

_KIND_DESCRIPTIONS: dict[str, str] = {
    ImportKind.INVOICES.value:  "Bills you've sent to clients",
    ImportKind.CUSTOMERS.value: "Names, emails and addresses of your buyers",
    ImportKind.PRODUCTS.value:  "Items or services you sell, with prices and SKUs",
    ImportKind.STOCK.value:     "Current stock levels for each product SKU",
}


# ── public entry-point ────────────────────────────────────────────────────────

def render() -> None:
    """Render setup, extraction review, and confirmation states."""

    _initialize_state()
    render_page_header(
        t("onboarding.eyebrow"),
        t("onboarding.title"),
        t("onboarding.subtitle"),
    )

    if _business_id() is None:
        _render_step1_profile()
        return
    _render_import_flow()


# ── session state ─────────────────────────────────────────────────────────────

def _initialize_state() -> None:
    st.session_state.setdefault("onboarding_business_id", None)
    st.session_state.setdefault("onboarding_preview", None)
    st.session_state.setdefault("onboarding_confirmation", None)
    st.session_state.setdefault("onboarding_step", 2)


def _business_id() -> UUID | None:
    value = st.session_state["onboarding_business_id"]
    return UUID(value) if isinstance(value, str) else None


# ── Step 1 · Business profile ─────────────────────────────────────────────────

def _render_step1_profile() -> None:
    st.progress(25, text="Step 1 of 4 · Create your workspace")

    # ── Voice pre-fill (collapsed by default) ──
    with st.expander("🎙 Fill the name with your voice", expanded=False):
        obrd_transcript = render_voice_input(
            key="obrd_voice",
            label="Say your business name",
            help_text="Speak in English or Hindi, then click the button below.",
        )
        if obrd_transcript:
            if st.button("→ Use this as business name", key="obrd_fill_name", width="content"):
                st.session_state["obrd_biz_name"] = obrd_transcript
                st.rerun()

    with st.form("business_profile"):
        left, right = st.columns(2, gap="large")
        with left:
            name = st.text_input(
                "Business name *",
                placeholder="e.g. Northstar Studio",
                key="obrd_biz_name",
            )
            email = st.text_input(
                "Contact email",
                placeholder="you@company.com",
                help="Optional — used for notifications only.",
            )
        with right:
            currency = st.selectbox(
                "Operating currency",
                ["USD", "EUR", "INR"],
                help="All prices and invoices will use this currency.",
            )
            st.selectbox(
                "Team size",
                ["Just me", "2–10 people", "11–50 people", "51+ people"],
            )

        submitted = st.form_submit_button("Create workspace →", type="primary")

    if submitted:
        if not name.strip():
            st.error("Please enter a business name to continue.")
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


# ── Step 2 · Import data ───────────────────────────────────────────────────────

def _render_import_flow() -> None:
    current_step = st.session_state.get("onboarding_step", 2)

    if current_step == 2:
        _render_step2_import()
    elif current_step == 3:
        _render_step3_review()
    elif current_step == 4:
        _render_step4_done()


def _render_step2_import() -> None:
    st.progress(50, text="Step 2 of 4 · Import your data (optional)")
    st.success("✅ Workspace created! Now let's bring in your existing data.")

    # ── What can be imported ──────────────────────────────────────────────
    render_section_title("Upload a file to import your data")

    st.markdown(
        "Upload a **PDF** (invoices, reports, catalogues) or a **CSV** export from "
        "any accounting / ERP tool.  The AI will read it automatically and let you "
        "review every row before anything is saved."
    )

    # ── File uploader ─────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "pdf"],
        help="PDF: the AI extracts data from any layout.  CSV: standard columnar import.",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        file_ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        is_pdf = file_ext == "pdf"

        # For PDFs show the auto-detect note; for CSV let user pick the kind
        if is_pdf:
            st.info(
                "🤖 **AI-powered import** — the AI will read your PDF and detect "
                "whether it contains invoices, customers, products, or stock levels. "
                "You can review and edit every row before saving.",
                icon=None,
            )
            # Still let the user override if they want
            with st.expander("Override detected type (optional)", expanded=False):
                kind_override = ImportKind(
                    st.selectbox(
                        "Force import as",
                        options=[k.value for k in ImportKind],
                        format_func=lambda v: _KIND_LABELS[v],
                        key="pdf_kind_override",
                    )
                )
            kind = kind_override
        else:
            # CSV — user must pick the kind
            render_section_title("What type of data is in this file?")
            cols = st.columns(2)
            kind_value = None
            for idx, (k, label) in enumerate(_KIND_LABELS.items()):
                col = cols[idx % 2]
                with col:
                    with st.container(border=True):
                        st.markdown(f"**{label}**")
                        st.caption(_KIND_DESCRIPTIONS[k])
                        if st.button("Select", key=f"kind_select_{k}", use_container_width=True):
                            st.session_state["selected_import_kind"] = k
                            st.rerun()

            # Resolve selected kind
            kind_raw = st.session_state.get("selected_import_kind", ImportKind.INVOICES.value)
            kind = ImportKind(kind_raw)
            st.caption(f"Currently selected: **{_KIND_LABELS[kind.value]}**")

        if st.button(
            "🔍 Extract & review" if is_pdf else "📥 Import & review",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Reading your file…" if not is_pdf else "AI is reading your PDF — this takes a few seconds…"):
                _create_preview(kind, uploaded_file.name, uploaded_file.getvalue())
            st.rerun()

    # ── Preview (shown after extraction) ─────────────────────────────────
    preview = st.session_state["onboarding_preview"]
    if isinstance(preview, ExtractionPreview):
        _render_preview(preview)

    # ── Skip option ───────────────────────────────────────────────────────
    st.divider()
    st.caption("Don't have a file yet? That's fine — you can add data manually later.")
    if st.button("Skip import and finish setup →", use_container_width=True):
        st.session_state["onboarding_step"] = 4
        st.rerun()


# ── Step 3 · Post-import review ───────────────────────────────────────────────

def _render_step3_review() -> None:
    st.progress(75, text="Step 3 of 4 · Import complete")
    confirmation: ImportConfirmation | None = st.session_state.get("onboarding_confirmation")

    if isinstance(confirmation, ImportConfirmation):
        st.success(
            f"✅ Import complete: **{confirmation.created}** created, "
            f"**{confirmation.updated}** updated, **{confirmation.skipped}** skipped."
        )
        for message in confirmation.messages:
            st.info(message)

    col_next, col_more = st.columns(2)
    with col_next:
        if st.button("Finish setup →", type="primary", use_container_width=True):
            st.session_state["onboarding_step"] = 4
            st.rerun()
    with col_more:
        if st.button("Import another file", use_container_width=True):
            st.session_state["onboarding_confirmation"] = None
            st.session_state["onboarding_step"] = 2
            st.session_state["onboarding_preview"] = None
            st.rerun()


# ── Step 4 · Done ─────────────────────────────────────────────────────────────

def _render_step4_done() -> None:
    st.progress(100, text="Step 4 of 4 · You're all set!")
    st.balloons()
    st.success("🎉 Your workspace is ready — your AI operations employee is standing by.")

    render_section_title("What can you do now?")

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**📊 Business Dashboard**")
            st.caption("Live snapshot of open invoices, low inventory, and outstanding balances.")
        with st.container(border=True):
            st.markdown("**🤖 AI Commands**")
            st.caption("Natural-language instructions: create customers, invoices, reminders and more.")
    with c2:
        with st.container(border=True):
            st.markdown("**👥 Customers / 📦 Products / 📄 Invoices**")
            st.caption("Browse, search, and manage your imported data directly.")
        with st.container(border=True):
            st.markdown("**🧠 Business Memory**")
            st.caption("Add context the AI can retrieve mid-conversation.")

    col_dash, col_home = st.columns(2)
    with col_dash:
        if st.button("Go to Dashboard", type="primary", use_container_width=True):
            st.session_state["_nav_pending"] = "Business Dashboard"
            st.rerun()
    with col_home:
        if st.button("Go to Home", use_container_width=True):
            st.session_state["_nav_pending"] = "Home"
            st.rerun()


# ── Extraction helpers ────────────────────────────────────────────────────────

def _create_preview(kind: ImportKind, file_name: str, content: bytes) -> None:
    """Extract a file into an in-memory review result without persistence."""
    try:
        preview = create_extraction_registry().extract(kind, file_name, content)
        st.session_state["onboarding_preview"] = preview
        st.session_state["onboarding_confirmation"] = None

        # If AI detected a different kind, update the session kind selector
        if preview.detected_kind is not None:
            st.session_state["selected_import_kind"] = preview.detected_kind.value

        bid = _business_id()
        extension = file_name.rsplit(".", maxsplit=1)[-1] if "." in file_name else ""
        pendo.track(
            "onboarding_file_extracted",
            account_id=str(bid) if bid else "system",
            properties={
                "import_kind": kind.value,
                "detected_kind": (preview.detected_kind or kind).value,
                "file_name": file_name,
                "file_extension": extension,
                "record_count": len(preview.records),
                "is_supported": preview.is_supported,
                "warning_count": len(preview.warnings),
            },
        )
    except Exception as error:
        st.error(f"Could not read that file: {error}")


def _to_safe_records(
    records: list[dict[str, object]],
) -> list[dict[str, str | float | int | bool | None]]:
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

    render_section_title("Review before saving")

    # Detected-kind banner
    if preview.detected_kind is not None:
        st.info(
            f"🤖 AI detected: **{_KIND_LABELS[preview.detected_kind.value]}** "
            f"— you can edit any row before saving.",
        )

    if not preview.is_supported:
        for warning in preview.warnings:
            st.warning(warning)
        if st.button("← Try another file", use_container_width=True):
            st.session_state["onboarding_preview"] = None
            st.rerun()
        return

    if preview.warnings:
        for warning in preview.warnings:
            st.warning(warning)

    records = [asdict(record) for record in preview.records] if preview.records else []

    if records:
        if "customer_name" not in records[0]:
            for row in records:
                row.setdefault("customer_name", "Default Customer")
        safe_records = _to_safe_records(records)

        st.caption(f"**{len(safe_records)} record(s) found.** Edit any cell before saving.")
        try:
            _ = st.data_editor(
                safe_records,
                num_rows="dynamic",
                use_container_width=True,
                key="onboarding_preview_editor",
            )
        except Exception as exc:
            st.error(f"Preview render failed: {exc}")

        col_confirm, col_discard = st.columns([2, 1])
        with col_confirm:
            if st.button("✅ Save to workspace", type="primary", use_container_width=True):
                _confirm_preview(preview)
        with col_discard:
            if st.button("✗ Discard", use_container_width=True):
                st.session_state["onboarding_preview"] = None
                st.rerun()
    else:
        st.info("No rows were found in this file. Nothing will be saved.")
        col_next, col_back = st.columns(2)
        with col_next:
            if st.button("Continue anyway →", type="primary", use_container_width=True):
                st.session_state["onboarding_step"] = 3
                st.session_state["onboarding_preview"] = None
                st.rerun()
        with col_back:
            if st.button("← Try another file", use_container_width=True):
                st.session_state["onboarding_preview"] = None
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
