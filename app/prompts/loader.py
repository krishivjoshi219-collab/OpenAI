"""Load version-controlled prompt templates from the prompts package."""

from __future__ import annotations

from importlib.resources import files
from string import Formatter


def render_prompt(name: str, **variables: str) -> str:
    """Load and render a named Markdown prompt with explicit variables only."""

    normalized_name = name.replace("_", "").replace("-", "")
    if not normalized_name.isalnum():
        raise ValueError(
            "Prompt names may only contain letters, numbers, underscores, and hyphens."
        )
    template = files("app.prompts").joinpath(f"{name}.md").read_text(encoding="utf-8")
    required = {field_name for _, field_name, _, _ in Formatter().parse(template) if field_name}
    missing = required.difference(variables)
    if missing:
        raise ValueError(f"Missing prompt variables: {', '.join(sorted(missing))}")
    return template.format(**variables)
