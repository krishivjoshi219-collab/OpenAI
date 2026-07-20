"""Code Viewer page — browse the full project source with a searchable summary."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.ui.components.layout import render_page_header, render_section_title

# ---------------------------------------------------------------------------
# Project root (two levels above this file: app/ui/pages → workspace root)
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent.parent.parent

# Directories and files to include, in display order
_SECTIONS: list[tuple[str, list[str]]] = [
    ("Configuration", ["config/settings.py", ".env.example"]),
    ("Application entry point", ["app/ui/streamlit_app.py"]),
    ("UI — Pages", [
        "app/ui/pages/home.py",
        "app/ui/pages/onboarding.py",
        "app/ui/pages/dashboard.py",
        "app/ui/pages/customers.py",
        "app/ui/pages/products.py",
        "app/ui/pages/invoices.py",
        "app/ui/pages/business_memory.py",
        "app/ui/pages/government_assistant.py",
        "app/ui/pages/settings.py",
        "app/ui/pages/code_viewer.py",
    ]),
    ("UI — Components", [
        "app/ui/components/layout.py",
        "app/ui/components/styles.py",
        "app/ui/components/widgets.py",
        "app/ui/components/pendo.py",
    ]),
    ("AI layer", [
        "app/ai/client.py",
        "app/ai/service.py",
        "app/ai/chat_adapter.py",
        "app/ai/adapters.py",
        "app/ai/contracts.py",
        "app/ai/tools.py",
        "app/ai/odoo_tools.py",
    ]),
    ("Services", [
        "app/services/dashboard.py",
        "app/services/government.py",
        "app/services/invoice_image.py",
        "app/services/invoice_pdf.py",
    ]),
    ("Onboarding", [
        "app/onboarding/extraction.py",
        "app/onboarding/service.py",
    ]),
    ("Business logic", [
        "app/business/engine.py",
        "app/business/commands.py",
        "app/business/services.py",
        "app/business/odoo.py",
    ]),
    ("Memory / RAG", [
        "app/memory/service.py",
        "app/memory/retriever.py",
        "app/memory/repository.py",
        "app/memory/contracts.py",
    ]),
    ("Notifications", [
        "app/notifications/service.py",
        "app/notifications/telegram.py",
        "app/notifications/client.py",
        "app/notifications/contracts.py",
    ]),
    ("Database", [
        "app/database/session.py",
        "app/database/repositories.py",
        "app/database/base.py",
    ]),
    ("Models", [
        "app/models/business.py",
        "app/models/customer.py",
        "app/models/invoice.py",
        "app/models/invoice_item.py",
        "app/models/product.py",
        "app/models/inventory.py",
        "app/models/supplier.py",
        "app/models/reminder.py",
        "app/models/business_memory.py",
        "app/models/settings.py",
        "app/models/enums.py",
    ]),
    ("Migrations", [
        "migrations/env.py",
        "migrations/versions/20260718_0001_initial_operations_schema.py",
        "migrations/versions/20260718_0002_memory_lookup_index.py",
        "migrations/versions/20260718_0003_reminders.py",
    ]),
    ("Tests", [
        "tests/test_smoke.py",
        "tests/test_ai_service.py",
        "tests/test_business_engine.py",
        "tests/test_business_memory.py",
        "tests/test_dashboard.py",
        "tests/test_database_layer.py",
        "tests/test_government_assistant.py",
        "tests/test_notifications.py",
        "tests/test_odoo_integration.py",
        "tests/test_onboarding_imports.py",
    ]),
]

# High-level module summaries shown in the overview table
_MODULE_SUMMARIES: list[dict[str, str]] = [
    {"Module": "config/", "Purpose": "App-wide settings loaded from environment variables (AI provider, keys, DB URL)."},
    {"Module": "app/ui/", "Purpose": "Streamlit pages and shared components — layout, styles, widgets."},
    {"Module": "app/ai/", "Purpose": "AI provider abstraction: OpenAI Responses API + Chat Completions adapter for Groq/Gemini."},
    {"Module": "app/services/", "Purpose": "Domain services: dashboard snapshots, government guidance, invoice image/PDF export."},
    {"Module": "app/onboarding/", "Purpose": "File extraction (CSV + PDF) and confirmation flow for seeding business data."},
    {"Module": "app/business/", "Purpose": "Core business engine, natural-language commands, Odoo integration helpers."},
    {"Module": "app/memory/", "Purpose": "Keyword-based RAG retriever and business-scoped memory CRUD."},
    {"Module": "app/notifications/", "Purpose": "Notification service with a Telegram channel adapter."},
    {"Module": "app/database/", "Purpose": "SQLAlchemy session factory, repositories, and Alembic migration wiring."},
    {"Module": "app/models/", "Purpose": "SQLAlchemy ORM models for all business entities (customers, invoices, products …)."},
    {"Module": "migrations/", "Purpose": "Alembic migration scripts — schema history for the PostgreSQL database."},
    {"Module": "tests/", "Purpose": "22 pytest unit tests covering AI, onboarding, database, notifications, and more."},
]


def _lang(path: str) -> str:
    """Map file extension to a Streamlit code-block language tag."""
    ext = path.rsplit(".", 1)[-1].lower()
    return {"py": "python", "md": "markdown", "toml": "toml", "env": "bash"}.get(ext, "text")


def _read(rel: str) -> str | None:
    full = _ROOT / rel
    try:
        return full.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _count_lines(rel: str) -> int:
    src = _read(rel)
    return src.count("\n") + 1 if src else 0


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the searchable project code viewer."""

    render_page_header(
        "Source",
        "View Code",
        "Browse every file in the project — search by name or content, then expand to read.",
    )

    # --- Summary table -------------------------------------------------------
    render_section_title("Project overview")
    st.dataframe(
        _MODULE_SUMMARIES,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Module": st.column_config.TextColumn("Module", width="small"),
            "Purpose": st.column_config.TextColumn("Purpose", width="large"),
        },
    )

    # Quick stats row
    all_paths = [p for _, paths in _SECTIONS for p in paths]
    total_lines = sum(_count_lines(p) for p in all_paths)
    total_files = len(all_paths)
    c1, c2, c3 = st.columns(3)
    c1.metric("Files", total_files)
    c2.metric("Lines of code", f"{total_lines:,}")
    c3.metric("Test count", "22")

    st.divider()

    # --- Search --------------------------------------------------------------
    render_section_title("Browse source files")
    query = st.text_input(
        "Filter by file name or content",
        placeholder="e.g. invoice, extract, pdf …",
        label_visibility="collapsed",
    ).strip().lower()

    # --- Sections ------------------------------------------------------------
    for section_name, paths in _SECTIONS:
        # Filter paths based on search query
        visible = []
        for rel in paths:
            src = _read(rel) or ""
            if not query or query in rel.lower() or query in src.lower():
                visible.append(rel)

        if not visible:
            continue

        render_section_title(section_name)
        for rel in visible:
            src = _read(rel)
            exists = src is not None
            label_icon = "📄" if exists else "⚠️"
            line_count = src.count("\n") + 1 if src else 0
            label = f"{label_icon}  `{rel}`" + (f"  —  {line_count:,} lines" if exists else "  —  file not found")

            with st.expander(label, expanded=False):
                if not exists:
                    st.warning(f"`{rel}` was not found on disk.")
                else:
                    # Highlight matching lines when searching
                    if query:
                        lines = src.splitlines()
                        hits = [i + 1 for i, ln in enumerate(lines) if query in ln.lower()]
                        if hits:
                            st.caption(f"Query **{query!r}** found on lines: {', '.join(str(n) for n in hits[:20])}" +
                                       (" …" if len(hits) > 20 else ""))
                    st.code(src, language=_lang(rel), line_numbers=True)
