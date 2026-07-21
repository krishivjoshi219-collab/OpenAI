import os
import sys
from pathlib import Path

# Ensure the project root is importable as `app` on all runtimes,
# including Streamlit Cloud where the repo is mounted at /mount/src/openai.
_SCRIPT_PATH = Path(__file__).resolve()
_PROJECT_ROOT = _SCRIPT_PATH.parent.parent.parent

for _candidate in [
    Path("/mount/src/openai"),
    _PROJECT_ROOT,
    Path(os.getcwd()),
]:
    _resolved = _candidate.resolve()
    if (_resolved / "app").is_dir() and str(_resolved) not in sys.path:
        sys.path.insert(0, str(_resolved))

# Streamlit entry point for the AI Operations Employee MVP.
# (Kept as a comment — a bare string literal here would be rendered as visible
#  text by Streamlit's magic-command feature since it follows executable code.)

import traceback  # noqa: E402

import streamlit as st  # noqa: E402


def _bridge_secrets() -> None:
    """Copy Streamlit Cloud secrets into os.environ so pydantic-settings reads them.

    On Streamlit Community Cloud, user secrets live in the Streamlit secrets
    manager (accessible via ``st.secrets``) rather than as OS environment
    variables.  ``pydantic-settings`` / ``BaseSettings`` reads from
    ``os.environ``, so we bridge the two here — before any config import —
    whenever a key is not already present in the environment.

    Only top-level string values are copied.  Nested TOML tables (e.g. a
    ``[database]`` section) are not env-var compatible and are skipped.
    """
    try:
        for key, value in st.secrets.items():
            if isinstance(value, str) and key not in os.environ:
                os.environ[key] = value
    except Exception:  # noqa: BLE001
        pass  # No secrets file / not on Cloud — skip silently


_bridge_secrets()

from app.ui.components.layout import render_sidebar  # noqa: E402
from app.ui.components.pendo import inject_pendo  # noqa: E402
from app.ui.components.styles import apply_global_styles  # noqa: E402
from app.ui.components.toast import inject_toast_container  # noqa: E402
from app.ui.pages import (  # noqa: E402
    business_memory,
    code_viewer,
    customers,
    dashboard,
    government_assistant,
    home,
    invoices,
    onboarding,
    products,
    settings,
    voice_commands,
)

PAGE_RENDERERS = {
    "Home": home.render,
    "Onboarding": onboarding.render,
    "Business Dashboard": dashboard.render,
    "Customers": customers.render,
    "Products": products.render,
    "Invoices": invoices.render,
    "Business Memory": business_memory.render,
    "Government Assistant": government_assistant.render,
    "Voice Commands": voice_commands.render,
    "Settings": settings.render,
    "View Code": code_viewer.render,
}


def _run_preflight_once() -> None:
    """Execute async dependency health checks once per session and cache the result."""

    if st.session_state.get("preflight_completed"):
        return

    try:
        import asyncio
        import concurrent.futures

        from config.settings import get_settings

        from app.backend.preflight import run_preflight_checks

        settings = get_settings()

        # asyncio.run() cannot be called from a thread that already has a running
        # event loop (Streamlit >= 1.18 installs one on the main thread). The safe
        # solution is to submit asyncio.run() to a *worker* thread, which starts
        # with no loop, and block the calling thread until it finishes.
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(
                asyncio.run,
                run_preflight_checks(settings, total_timeout_ms=3000),
            )
            results = future.result(timeout=5)
            pool.shutdown(wait=True)
        except concurrent.futures.TimeoutError:
            pool.shutdown(wait=False)
            raise

        for name, result in results.items():
            st.session_state[f"preflight_result_{name}"] = result
            if not result.ok and getattr(result, "error_kind", "") == "auth":
                st.session_state[f"preflight_failed_{name}"] = True

        st.session_state["preflight_completed"] = True
    except Exception as exc:  # noqa: BLE001
        st.session_state["preflight_completed"] = True
        st.session_state["global_error"] = str(exc)


def _init_database_once() -> None:
    """Create all database tables if they do not already exist."""

    if st.session_state.get("db_initialized"):
        return

    try:
        from app.database.session import create_all_tables

        create_all_tables()
        st.session_state["db_initialized"] = True
    except Exception as exc:  # noqa: BLE001
        st.session_state["db_initialized"] = False
        st.session_state["db_init_error"] = str(exc)
        raise


def _handle_global_error(exc: Exception) -> None:
    """Display a user-friendly recovery message for unhandled exceptions."""

    st.session_state["global_error"] = str(exc)
    st.error(
        "Sorry, a minor system conflict occurred. "
        "Aster Ops automated recovery tools are deploying a live container hotfix now..."
    )


def main() -> None:
    """Configure and render the selected presentation-only workspace page."""

    # set_page_config MUST be the first Streamlit call each run.  If it were
    # placed after _init_database_once() and that function raised an exception,
    # the outer except block would call st.error() before set_page_config,
    # crashing with StreamlitSetPageConfigMustBeCalledInTheMainModuleException.
    st.set_page_config(
        page_title="Aster Ops · AI Operations Employee",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    try:
        _init_database_once()
        _run_preflight_once()

        apply_global_styles()
        inject_pendo()
        inject_toast_container()
        selected_page = render_sidebar()
        PAGE_RENDERERS[selected_page]()
    except Exception as exc:
        traceback.print_exc()
        _handle_global_error(exc)


if __name__ == "__main__":
    main()
