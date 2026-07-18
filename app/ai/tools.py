"""Tool registry and execution boundary for present and future application tools."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Callable

from app.ai.contracts import ActionLogEntry, ToolDefinition, ToolHandler


@dataclass(frozen=True)
class RegisteredTool:
    """Pair a model-visible declaration with its application-side handler."""

    definition: ToolDefinition
    handler: ToolHandler | Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """Own tool registration so AI orchestration never imports business services directly."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        definition: ToolDefinition,
        handler: ToolHandler | Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
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


class ActionLogger:
    """Emit one JSON application-log event for every attempted AI action."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("app.ai.actions")

    def log(self, entry: ActionLogEntry) -> None:
        """Write an audit-safe structured event to the application's normal logs."""

        self._logger.info("ai_business_action %s", json.dumps(asdict(entry), default=str))
