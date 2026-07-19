#!/usr/bin/env python3
"""Stateful orchestration system with explicit StateGraph architecture.

Nodes:
  - DiagnoseNode: parses traceback logs, identifies target file and error kind
  - AIFixerNode: constructs source modifications matching repository structure
  - TestRunnerNode: executes pytest programmatically and captures results
  - GitSyncNode: formats and syncs the PR branch

Transitions:
  START  -> DiagnoseNode
  DiagnoseNode -> AIFixerNode
  AIFixerNode -> TestRunnerNode
  TestRunnerNode -> AIFixerNode  (on test/compilation failure)
  TestRunnerNode -> GitSyncNode  (on success)
  GitSyncNode -> END
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import traceback
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# Global system state
# ---------------------------------------------------------------------------


class NodeName(StrEnum):
    """Enumeration of all graph nodes."""

    DIAGNOSE = "diagnose"
    FIXER = "fixer"
    TEST_RUNNER = "test_runner"
    GIT_SYNC = "git_sync"
    END = "end"


class TestStatus(StrEnum):
    """Possible test execution outcomes."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class SystemState(TypedDict):
    """Immutable snapshot of the orchestration state at any graph node."""

    target_file: str | None
    raw_error: str | None
    current_patch: str | None
    test_status: TestStatus
    node_history: list[NodeName]
    retry_count: int
    max_retries: int
    git_branch: str | None
    diagnosis: str | None
    patch_plan: str | None
    test_output: str | None
    error_kind: str | None


def initial_state(max_retries: int = 3) -> SystemState:
    """Return a fresh orchestration state."""

    return SystemState(
        target_file=None,
        raw_error=None,
        current_patch=None,
        test_status=TestStatus.PENDING,
        node_history=[],
        retry_count=0,
        max_retries=max_retries,
        git_branch=None,
        diagnosis=None,
        patch_plan=None,
        test_output=None,
        error_kind=None,
    )


# ---------------------------------------------------------------------------
# Node protocols and implementations
# ---------------------------------------------------------------------------


NodeFunc = Callable[[SystemState], SystemState]


class NodeResult:
    """Outcome of executing one graph node."""

    def __init__(self, state: SystemState, next_node: NodeName) -> None:
        self.state = state
        self.next_node = next_node


# ------------------------------
# Diagnose Node
# ------------------------------


class DiagnoseNode:
    """Parse traceback logs and extract target file, error kind, and diagnosis."""

    _TRACEBACK_FILE_RE = re.compile(r'File "([^"]+)"', re.MULTILINE)
    _STREAMLIT_ERROR_RE = re.compile(r"ModuleNotFoundError: No module named ['\"]?([^'\"]+)['\"]?")
    _SQLALCHEMY_ERROR_RE = re.compile(r"sqlite3\.OperationalError: (.+?)(?:\n|$)")
    _STREAMLIT_INVALID_HEIGHT_RE = re.compile(
        r"StreamlitInvalidHeightError: (.+?)(?:\n|$)"
    )
    _CONFIG_OPTION_RE = re.compile(r'"([^"]+)" is not a valid config option')

    def run(self, state: SystemState) -> NodeResult:
        """Analyse the raw error and populate state fields."""

        raw_error = state.get("raw_error") or ""
        diagnosis_parts: list[str] = []

        # Extract target file from traceback
        file_matches = self._TRACEBACK_FILE_RE.findall(raw_error)
        repo_files = [
            f for f in file_matches if f.startswith("/mount/src/openai/")
        ]
        if repo_files:
            target_file = repo_files[-1]
            state["target_file"] = os.path.relpath(
                target_file, "/mount/src/openai"
            )
            diagnosis_parts.append(f"Target file: {state['target_file']}")
        elif "ModuleNotFoundError: No module named 'app'" in raw_error:
            state["target_file"] = "app/ui/streamlit_app.py"
            diagnosis_parts.append(
                "Target file inferred: app/ui/streamlit_app.py "
                "(entry point missing sys.path fix)"
            )

        # Detect error kind
        error_kind = "unknown"
        if self._STREAMLIT_ERROR_RE.search(raw_error):
            error_kind = "module_not_found"
            diagnosis_parts.append(
                "Detected: Streamlit module import failure (app package not on sys.path)."
            )
        elif self._SQLALCHEMY_ERROR_RE.search(raw_error):
            error_kind = "database_schema"
            match = self._SQLALCHEMY_ERROR_RE.search(raw_error)
            if match:
                diagnosis_parts.append(f"Detected: SQLite schema error — {match.group(1)}")
        elif self._STREAMLIT_INVALID_HEIGHT_RE.search(raw_error):
            error_kind = "streamlit_api"
            match = self._STREAMLIT_INVALID_HEIGHT_RE.search(raw_error)
            if match:
                diagnosis_parts.append(f"Detected: Streamlit API error — {match.group(1)}")
        elif self._CONFIG_OPTION_RE.search(raw_error):
            error_kind = "config_option"
            match = self._CONFIG_OPTION_RE.search(raw_error)
            if match:
                diagnosis_parts.append(
                    f"Detected: Invalid Streamlit config option — {match.group(1)}"
                )
        elif "Odoo HTTP error 404" in raw_error:
            error_kind = "odoo_connectivity"
            diagnosis_parts.append(
                "Detected: Odoo endpoint unreachable (HTTP 404). "
                "This is expected when ODOO_URL is a placeholder."
            )
        elif "Odoo HTTP error 401" in raw_error:
            error_kind = "odoo_auth"
            diagnosis_parts.append(
                "Detected: Odoo authentication failure (HTTP 401). "
                "Trigger BYOK fallback in the sidebar."
            )
        elif "429" in raw_error or "rate limit" in raw_error.lower():
            error_kind = "rate_limit"
            diagnosis_parts.append(
                "Detected: Rate-limit response from external API. "
                "Trigger BYOK fallback or backoff."
            )

        state["error_kind"] = error_kind
        state["diagnosis"] = "\n".join(diagnosis_parts) if diagnosis_parts else "No specific pattern matched."

        # Always proceed to fixer
        state["node_history"] = state.get("node_history", []) + [NodeName.DIAGNOSE]
        return NodeResult(state=state, next_node=NodeName.FIXER)


# ------------------------------
# AI Fixer Node
# ------------------------------


class AIFixerNode:
    """Construct clean source modifications matching the repository structure."""

    def run(self, state: SystemState) -> NodeResult:
        """Generate a patch plan and current_patch based on diagnosis."""

        target = state.get("target_file") or "app/ui/streamlit_app.py"
        error_kind = state.get("error_kind") or "unknown"
        diagnosis = state.get("diagnosis") or ""

        patch_plan_parts = [
            f"# Fix plan for {target}",
            f"# Error kind: {error_kind}",
            f"# Diagnosis: {diagnosis}",
            "",
        ]

        patch_lines: list[str] = []
        rel_path = target

        if error_kind == "module_not_found":
            patch_plan_parts.extend(
                [
                    "## Action: Ensure project root is on sys.path before any app imports.",
                    "- Insert a dual-strategy sys.path block at the very top of the file.",
                    "- Primary: os.getcwd() (Streamlit Cloud container).",
                    "- Fallback: __file__-relative path (local development).",
                ]
            )
            patch_lines.extend(
                self._build_sys_path_patch(rel_path)
            )

        elif error_kind == "database_schema":
            patch_plan_parts.extend(
                [
                    "## Action: Ensure all SQLAlchemy tables exist before queries.",
                    "- Use Base.metadata.create_all(bind=engine) which is idempotent.",
                    "- Run this once at app startup before any page renders.",
                ]
            )
            patch_lines.extend(
                self._build_db_init_patch()
            )

        elif error_kind == "streamlit_api":
            patch_plan_parts.extend(
                [
                    "## Action: Replace deprecated Streamlit API calls.",
                    "- Replace st.components.v1.html with st.iframe.",
                    "- Use height='content' or a positive integer (not 0).",
                ]
            )
            patch_lines.extend(
                self._build_streamlit_iframe_patch(rel_path)
            )

        elif error_kind == "config_option":
            patch_plan_parts.extend(
                [
                    "## Action: Remove invalid config options from .streamlit/config.toml.",
                    "- showErrorDetails belongs under [client], not [global].",
                ]
            )
            patch_lines.extend(
                self._build_config_toml_patch()
            )

        elif error_kind == "odoo_connectivity":
            patch_plan_parts.extend(
                [
                    "## Action: Odoo 404 is expected with mock credentials.",
                    "- Classify as connectivity (not auth) to suppress BYOK warnings.",
                    "- Ensure error_kind is set to 'connectivity' in preflight checks.",
                ]
            )
            patch_lines.extend(
                self._build_odoo_preflight_patch()
            )

        elif error_kind == "odoo_auth":
            patch_plan_parts.extend(
                [
                    "## Action: Odoo auth failure should trigger BYOK sidebar warning.",
                    "- Ensure error_kind is 'auth' so preflight sets preflight_failed_odoo.",
                ]
            )
            patch_lines.extend(
                self._build_odoo_auth_patch()
            )

        else:
            patch_plan_parts.append(
                "## Action: Generic resilience patch — add global error shield."
            )
            patch_lines.extend(
                self._build_generic_error_shield_patch(rel_path)
            )

        state["patch_plan"] = "\n".join(patch_plan_parts)
        state["current_patch"] = "\n".join(patch_lines)
        state["node_history"] = state.get("node_history", []) + [NodeName.FIXER]
        return NodeResult(state=state, next_node=NodeName.TEST_RUNNER)


    @staticmethod
    def _build_sys_path_patch(rel_path: str) -> list[str]:
        return [
            "---",
            "+++",
            f"@@ --- {rel_path}",
            f"+++ {rel_path}",
            " import os",
            " import sys",
            "+# Ensure the project root is importable as `app` on all runtimes,",
            "+# including Streamlit Cloud where __file__ may resolve inside the container.",
            "+_cwd = os.getcwd()",
            "+if _cwd not in sys.path:",
            "+    sys.path.insert(0, _cwd)",
            "+",
            "+_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))",
            "+_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, '../..'))",
            "+if _PROJECT_ROOT not in sys.path:",
            "+    sys.path.insert(0, _PROJECT_ROOT)",
            "",
        ]

    @staticmethod
    def _build_db_init_patch() -> list[str]:
        return [
            "---",
            "+++",
            "@@ --- app/database/session.py",
            "+++ app/database/session.py",
            " def create_all_tables(engine: Engine | None = None) -> None:",
            '     """Create all SQLAlchemy model tables if they do not already exist."""',
            "     from app.database.base import Base",
            "     db_engine = engine or create_engine_from_settings()",
            "     Base.metadata.create_all(bind=db_engine)",
            "",
        ]

    @staticmethod
    def _build_streamlit_iframe_patch(rel_path: str) -> list[str]:
        return [
            "---",
            "+++",
            f"@@ --- {rel_path}",
            f"+++ {rel_path}",
            "-    st.components.v1.html(...)",
            "+    st.iframe(src=..., height=1)",
            "",
        ]

    @staticmethod
    def _build_config_toml_patch() -> list[str]:
        return [
            "---",
            "+++",
            "@@ --- .streamlit/config.toml",
            "+++ .streamlit/config.toml",
            " [global]",
            "+",
            " [client]",
            ' showErrorDetails = "none"',
            ' showSidebarNavigation = false',
            "",
        ]

    @staticmethod
    def _build_odoo_preflight_patch() -> list[str]:
        return [
            "---",
            "+++",
            "@@ --- app/backend/preflight.py",
            "+++ app/backend/preflight.py",
            "     error_kind = 'connectivity'",
            "     return PreflightResult('odoo', False, latency, error_str, status, error_kind)",
            "",
        ]

    @staticmethod
    def _build_odoo_auth_patch() -> list[str]:
        return [
            "---",
            "+++",
            "@@ --- app/backend/preflight.py",
            "+++ app/backend/preflight.py",
            "     error_kind = 'auth'",
            "     return PreflightResult('odoo', False, latency, error_str, status, error_kind)",
            "",
        ]

    @staticmethod
    def _build_generic_error_shield_patch(rel_path: str) -> list[str]:
        return [
            "---",
            "+++",
            f"@@ --- {rel_path}",
            f"+++ {rel_path}",
            " def main() -> None:",
            '     """Configure and render the selected presentation-only workspace page."""',
            "     try:",
            "         _init_database_once()",
            "         _run_preflight_once()",
            "         st.set_page_config(...)",
            "         apply_global_styles()",
            "         inject_pendo()",
            "         inject_toast_container()",
            "         selected_page = render_sidebar()",
            "         PAGE_RENDERERS[selected_page]()",
            "     except Exception as exc:",
            "         import traceback",
            "         traceback.print_exc()",
            "         _handle_global_error(exc)",
            "",
        ]


# ------------------------------
# Test Runner Node
# ------------------------------


class TestRunnerNode:
    """Execute pytest programmatically and capture results."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path("/mount/src/openai")

    def run(self, state: SystemState) -> NodeResult:
        """Run pytest and update state with results."""

        state["test_status"] = TestStatus.RUNNING
        state["node_history"] = state.get("node_history", []) + [NodeName.TEST_RUNNER]

        test_dir = self._repo_root / "tests"
        if not test_dir.exists():
            state["test_status"] = TestStatus.ERROR
            state["test_output"] = f"Test directory not found: {test_dir}"
            return NodeResult(state=state, next_node=NodeName.FIXER)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_dir),
            "-x",
            "-q",
            "--tb=short",
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            output = proc.stdout + proc.stderr
            state["test_output"] = output

            if proc.returncode == 0:
                state["test_status"] = TestStatus.PASSED
                return NodeResult(state=state, next_node=NodeName.GIT_SYNC)
            state["test_status"] = TestStatus.FAILED
            state["retry_count"] = state.get("retry_count", 0) + 1
            if state.get("retry_count", 0) >= state.get("max_retries", 3):
                state["test_status"] = TestStatus.ERROR
                return NodeResult(state=state, next_node=NodeName.END)
            return NodeResult(state=state, next_node=NodeName.FIXER)
        except subprocess.TimeoutExpired:
            state["test_status"] = TestStatus.ERROR
            state["test_output"] = "pytest timed out after 120 seconds."
            return NodeResult(state=state, next_node=NodeName.FIXER)
        except Exception as exc:
            state["test_status"] = TestStatus.ERROR
            state["test_output"] = f"pytest execution error: {exc}"
            traceback.print_exc()
            return NodeResult(state=state, next_node=NodeName.FIXER)


# ------------------------------
# Git Sync Node
# ------------------------------


class GitSyncNode:
    """Format and sync the PR branch after successful validation."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path("/mount/src/openai")

    def run(self, state: SystemState) -> NodeResult:
        """Run git format and sync operations."""

        state["node_history"] = state.get("node_history", []) + [NodeName.GIT_SYNC]

        commands = [
            ["git", "add", "."],
            ["git", "status", "--porcelain"],
        ]

        results: list[str] = []
        for cmd in commands:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(self._repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                results.append(
                    f"$ {' '.join(cmd)}\n{proc.stdout}{proc.stderr}"
                )
            except Exception as exc:
                results.append(f"$ {' '.join(cmd)}\nERROR: {exc}")

        state["git_branch"] = self._get_current_branch()
        state["test_output"] = "\n".join(results)
        state["test_status"] = TestStatus.PASSED
        return NodeResult(state=state, next_node=NodeName.END)

    def _get_current_branch(self) -> str | None:
        """Return the current git branch name."""

        try:
            proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            branch = proc.stdout.strip()
            return branch if branch else None
        except Exception:
            return None


# ---------------------------------------------------------------------------
# StateGraph orchestration engine
# ---------------------------------------------------------------------------


class StateGraph:
    """Explicit graph-based orchestration engine with validation branching."""

    def __init__(self, max_retries: int = 3) -> None:
        self._nodes: dict[NodeName, NodeFunc] = {}
        self._max_retries = max_retries

    def add_node(self, name: NodeName, func: NodeFunc) -> None:
        """Register a named node function."""

        self._nodes[name] = func

    def execute(self, initial: SystemState) -> SystemState:
        """Run the graph from initial state until END or terminal error."""

        state = initial
        current = NodeName.DIAGNOSE

        while current != NodeName.END:
            if current not in self._nodes:
                raise ValueError(f"Unknown node: {current}")

            node_func = self._nodes[current]
            result = node_func(state)
            state = result.state
            current = result.next_node

        return state


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


def run_orchestration(
    raw_error: str,
    target_file: str | None = None,
    max_retries: int = 3,
) -> SystemState:
    """Run the full diagnose -> fix -> test -> sync pipeline."""

    state = initial_state(max_retries=max_retries)
    state["raw_error"] = raw_error
    if target_file:
        state["target_file"] = target_file

    graph = StateGraph(max_retries=max_retries)
    graph.add_node(NodeName.DIAGNOSE, DiagnoseNode().run)
    graph.add_node(NodeName.FIXER, AIFixerNode().run)
    graph.add_node(NodeName.TEST_RUNNER, TestRunnerNode().run)
    graph.add_node(NodeName.GIT_SYNC, GitSyncNode().run)

    return graph.execute(state)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the orchestrator."""

    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/orchestrator.py <traceback_file_or_string> [target_file]"
        )
        sys.exit(1)

    raw_error_input = sys.argv[1]
    target_file = sys.argv[2] if len(sys.argv) > 2 else None

    # If the argument is a file path, read its contents
    if os.path.isfile(raw_error_input):
        with open(raw_error_input, encoding="utf-8") as handle:
            raw_error_input = handle.read()

    final_state = run_orchestration(
        raw_error=raw_error_input,
        target_file=target_file,
    )

    print("\n" + "=" * 80)
    print("ORCHESTRATION COMPLETE")
    print("=" * 80)
    print(f"Target file : {final_state.get('target_file')}")
    print(f"Error kind   : {final_state.get('error_kind')}")
    print(f"Diagnosis    : {final_state.get('diagnosis')}")
    print(f"Patch plan   : {final_state.get('patch_plan')}")
    print(f"Test status  : {final_state.get('test_status')}")
    print(f"Retry count  : {final_state.get('retry_count')}")
    print(f"Git branch   : {final_state.get('git_branch')}")
    print(f"Node history : {' -> '.join(str(n) for n in final_state.get('node_history', []))}")
    print("=" * 80)


if __name__ == "__main__":
    main()
