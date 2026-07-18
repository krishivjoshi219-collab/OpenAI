"""OpenAI Responses API orchestration for business commands."""

from __future__ import annotations

import json
from typing import Any

from app import pendo
from app.ai.contracts import (
    ActionLogEntry,
    AIResult,
    AgentProfile,
    ConversationMessage,
    ConversationState,
    ResponsesClient,
    StructuredOutputSpec,
    ToolCall,
)
from app.ai.tools import ActionLogger, ToolRegistry
from app.prompts.loader import render_prompt


# Maximum number of model ↔ tool round-trips before the loop is aborted.
# Raised from 4 to 8 so that multi-step business commands (e.g. search → create
# invoice → add lines) have enough headroom without running forever.
_MAX_TOOL_TURNS = 8

DEFAULT_AGENT = AgentProfile(name="operations", prompt_name="business_command")
BUSINESS_RESPONSE = StructuredOutputSpec(
    name="business_action_response",
    description="The user-facing result of one business request.",
    schema={
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "outcome": {
                "type": "string",
                "enum": ["completed", "needs_input", "failed", "no_action"],
            },
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "reason": {"type": "string"},
                        "status": {"type": "string", "enum": ["completed", "failed"]},
                    },
                    "required": ["tool_name", "reason", "status"],
                    "additionalProperties": False,
                },
            },
            "next_steps": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "outcome", "actions", "next_steps"],
        "additionalProperties": False,
    },
)


class AIService:
    """Run business-language commands through the OpenAI Responses API."""

    def __init__(
        self,
        client: ResponsesClient,
        model: str,
        tool_registry: ToolRegistry | None = None,
        action_logger: ActionLogger | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._tool_registry = tool_registry or ToolRegistry()
        self._action_logger = action_logger or ActionLogger()

    def command(
        self,
        command: str,
        *,
        conversation: ConversationState | None = None,
        business_context: str = "",
        agent: AgentProfile = DEFAULT_AGENT,
        structured_output: StructuredOutputSpec | None = None,
        execute_tools: bool = False,
    ) -> AIResult:
        """Handle a natural-language business command and optionally execute registered tools."""

        if not command.strip():
            raise ValueError("A business command cannot be empty.")
        state = conversation or ConversationState()
        instructions = render_prompt(agent.prompt_name, business_context=business_context)
        tools = self._tool_registry.definitions_for(agent.tool_names)
        response = self._create_response(
            command,
            state,
            instructions,
            tools,
            structured_output,
        )
        tool_calls = self._extract_tool_calls(response)
        actions: tuple[ActionLogEntry, ...] = ()
        if execute_tools and tool_calls:
            response, actions = self._run_tool_loop(
                response, tool_calls, instructions, tools, structured_output
            )
            tool_calls = self._extract_tool_calls(response)
        result = self._to_result(response, state, command, tool_calls, structured_output, actions)
        pendo.track(
            "ai_business_command_executed",
            properties={
                "agent_name": agent.name,
                "model": self._model,
                "outcome": (result.structured_output or {}).get("outcome", ""),
                "tool_call_count": len(result.tool_calls),
                "actions_completed": sum(1 for a in actions if a.status == "completed"),
                "actions_failed": sum(1 for a in actions if a.status == "failed"),
                "has_structured_output": result.structured_output is not None,
                "conversation_message_count": len(result.conversation.messages),
            },
        )
        return result

    def business_command(
        self,
        command: str,
        *,
        conversation: ConversationState | None = None,
        business_context: str = "",
    ) -> AIResult:
        """Execute a business request and return the standard strict JSON result."""

        return self.command(
            command,
            conversation=conversation,
            business_context=business_context,
            structured_output=BUSINESS_RESPONSE,
            execute_tools=True,
        )

    def _create_response(
        self,
        command: str,
        state: ConversationState,
        instructions: str,
        tools: list[Any],
        structured_output: StructuredOutputSpec | None,
    ) -> Any:
        request: dict[str, Any] = {
            "model": self._model,
            "instructions": instructions,
            "input": self._build_input(command, state),
        }
        if state.previous_response_id is not None:
            request["previous_response_id"] = state.previous_response_id
        if tools:
            request["tools"] = [tool.as_responses_tool() for tool in tools]
        if structured_output is not None:
            request["text"] = {"format": structured_output.as_responses_format()}
        return self._client.responses.create(**request)

    def _run_tool_loop(
        self,
        response: Any,
        tool_calls: tuple[ToolCall, ...],
        instructions: str,
        tools: list[Any],
        structured_output: StructuredOutputSpec | None,
    ) -> tuple[Any, tuple[ActionLogEntry, ...]]:
        actions: list[ActionLogEntry] = []
        for _ in range(_MAX_TOOL_TURNS):
            outputs = []
            for call in tool_calls:
                try:
                    output = self._tool_registry.execute(call.name, call.arguments)
                    status = "completed"
                except Exception as error:  # Return a tool error so the model can recover safely.
                    output = {"status": "failed", "error": str(error)}
                    status = "failed"
                entry = ActionLogEntry(
                    call_id=call.call_id,
                    tool_name=call.name,
                    reason=str(call.arguments.get("reason", "No reason supplied by model.")),
                    arguments=call.arguments,
                    status=status,
                    output=output,
                )
                actions.append(entry)
                self._action_logger.log(entry)
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(output, default=str),
                    }
                )
            request: dict[str, Any] = {
                "model": self._model,
                "instructions": instructions,
                "previous_response_id": response.id,
                "input": outputs,
            }
            if tools:
                request["tools"] = [tool.as_responses_tool() for tool in tools]
            if structured_output is not None:
                request["text"] = {"format": structured_output.as_responses_format()}
            response = self._client.responses.create(**request)
            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                return response, tuple(actions)
        raise RuntimeError(
            f"Tool execution exceeded the maximum of {_MAX_TOOL_TURNS} response turns."
        )

    @staticmethod
    def _build_input(command: str, state: ConversationState) -> list[dict[str, str]]:
        if state.previous_response_id is not None:
            return [{"role": "user", "content": command}]
        messages = [
            {"role": message.role, "content": message.content}
            for message in state.messages
        ]
        return [*messages, {"role": "user", "content": command}]

    @staticmethod
    def _extract_tool_calls(response: Any) -> tuple[ToolCall, ...]:
        calls: list[ToolCall] = []
        for item in getattr(response, "output", []):
            if getattr(item, "type", None) != "function_call":
                continue
            try:
                arguments = json.loads(item.arguments)
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(
                    f"Tool {item.name} returned malformed JSON arguments: {exc}"
                ) from exc
            if not isinstance(arguments, dict):
                raise ValueError(f"Tool {item.name} returned non-object arguments.")
            calls.append(ToolCall(call_id=item.call_id, name=item.name, arguments=arguments))
        return tuple(calls)

    @staticmethod
    def _to_result(
        response: Any,
        state: ConversationState,
        command: str,
        tool_calls: tuple[ToolCall, ...],
        structured_output: StructuredOutputSpec | None,
        actions: tuple[ActionLogEntry, ...],
    ) -> AIResult:
        text = getattr(response, "output_text", "")
        parsed = json.loads(text) if structured_output is not None and text else None
        conversation = state.append(
            ConversationMessage(role="user", content=command),
            ConversationMessage(role="assistant", content=text),
            response_id=response.id,
        )
        return AIResult(
            text=text,
            conversation=conversation,
            tool_calls=tool_calls,
            structured_output=parsed,
            actions=actions,
        )
