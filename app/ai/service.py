"""OpenAI Responses API orchestration for business commands."""

from __future__ import annotations

import json
from typing import Any

from app.ai.contracts import (
    AIResult,
    AgentProfile,
    ConversationMessage,
    ConversationState,
    ResponsesClient,
    StructuredOutputSpec,
    ToolCall,
)
from app.ai.tools import ToolRegistry
from app.prompts.loader import render_prompt


DEFAULT_AGENT = AgentProfile(name="operations", prompt_name="business_command")


class AIService:
    """Run business-language commands through the OpenAI Responses API."""

    def __init__(
        self,
        client: ResponsesClient,
        model: str,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._tool_registry = tool_registry or ToolRegistry()

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
        if execute_tools and tool_calls:
            response = self._run_tool_loop(
                response, tool_calls, instructions, tools, structured_output
            )
            tool_calls = self._extract_tool_calls(response)
        return self._to_result(response, state, command, tool_calls, structured_output)

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
    ) -> Any:
        for _ in range(4):
            outputs = [
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(self._tool_registry.execute(call.name, call.arguments)),
                }
                for call in tool_calls
            ]
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
                return response
        raise RuntimeError("Tool execution exceeded the maximum number of response turns.")

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
            arguments = json.loads(item.arguments)
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
        )
