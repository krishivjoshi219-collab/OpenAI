"""Provider-neutral contracts for conversational AI orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ConversationMessage:
    """A single user or assistant message retained by the application."""

    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class ConversationState:
    """Conversation history with an optional Responses API continuation identifier."""

    messages: tuple[ConversationMessage, ...] = ()
    previous_response_id: str | None = None

    def append(
        self, *messages: ConversationMessage, response_id: str | None = None
    ) -> ConversationState:
        """Return an immutable state containing additional messages."""

        return ConversationState(
            messages=(*self.messages, *messages),
            previous_response_id=response_id or self.previous_response_id,
        )


@dataclass(frozen=True)
class ToolDefinition:
    """A function tool exposed to the model using a JSON Schema parameter contract."""

    name: str
    description: str
    parameters: dict[str, Any]
    strict: bool = True

    def as_responses_tool(self) -> dict[str, Any]:
        """Convert this definition into the Responses API function-tool shape."""

        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "strict": self.strict,
        }


@dataclass(frozen=True)
class ToolCall:
    """A model-requested function invocation awaiting application execution."""

    call_id: str
    name: str
    arguments: dict[str, Any]


class ToolHandler(Protocol):
    """Executes one validated application tool call."""

    def __call__(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return JSON-serializable output for the requested tool."""


@dataclass(frozen=True)
class StructuredOutputSpec:
    """Schema requested from the model through Responses structured outputs."""

    name: str
    schema: dict[str, Any]
    description: str | None = None

    def as_responses_format(self) -> dict[str, Any]:
        """Convert this specification into the Responses API text-format shape."""

        format_config: dict[str, Any] = {
            "type": "json_schema",
            "name": self.name,
            "schema": self.schema,
            "strict": True,
        }
        if self.description is not None:
            format_config["description"] = self.description
        return format_config


@dataclass(frozen=True)
class AgentProfile:
    """Configuration boundary for a future specialised agent."""

    name: str
    prompt_name: str
    tool_names: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class AIResult:
    """Normalized result returned by the AI service."""

    text: str
    conversation: ConversationState
    tool_calls: tuple[ToolCall, ...] = ()
    structured_output: dict[str, Any] | None = None


class ResponsesClient(Protocol):
    """Minimal OpenAI SDK surface needed by the application service."""

    responses: Any
