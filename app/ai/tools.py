"""Tool registry and execution boundary for present and future application tools."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.contracts import ToolDefinition, ToolHandler


@dataclass(frozen=True)
class RegisteredTool:
    """Pair a model-visible declaration with its application-side handler."""

    definition: ToolDefinition
    handler: ToolHandler


class ToolRegistry:
    """Own tool registration so AI orchestration never imports business services directly."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        """Register a unique tool declaration and executor."""

        if definition.name in self._tools:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._tools[definition.name] = RegisteredTool(definition=definition, handler=handler)

    def definitions_for(self, allowed_names: frozenset[str] | None = None) -> list[ToolDefinition]:
        """Return all tools or the explicitly allowed subset for an agent."""

        if allowed_names is None:
            return [tool.definition for tool in self._tools.values()]
        return [self._tools[name].definition for name in allowed_names if name in self._tools]

    def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        """Execute a registered tool or fail before an untrusted call reaches business code."""

        try:
            tool = self._tools[name]
        except KeyError as error:
            raise ValueError(f"The model requested an unavailable tool: {name}") from error
        return tool.handler(arguments)
