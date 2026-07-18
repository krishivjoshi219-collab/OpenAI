"""Chat Completions adapter implementing the ResponsesClient protocol.

Wraps any OpenAI-compatible Chat Completions client (Groq, Gemini, etc.) so
it satisfies the ResponsesClient surface expected by AIService, which is built
around the OpenAI Responses API.  Conversation state is maintained in-process
because Chat Completions APIs are stateless.
"""

from __future__ import annotations

import json
import uuid
from typing import Any


class _FunctionCallItem:
    """Mimics an OpenAI Responses API function-call output item."""

    type = "function_call"

    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.call_id = call_id
        self.name = name
        self.arguments = arguments  # raw JSON string, as in the Responses API


class _ChatResponse:
    """Mimics the minimal OpenAI Responses API response surface AIService uses."""

    def __init__(
        self,
        response_id: str,
        output: list[Any],
        output_text: str,
    ) -> None:
        self.id = response_id
        self.output = output
        self.output_text = output_text


class _ChatCompletionsResource:
    """Implements the `.responses.create()` surface via Chat Completions."""

    def __init__(self, client: Any) -> None:
        self._client = client
        # Maps response_id → full message list (including the assistant turn).
        self._history: dict[str, list[dict[str, Any]]] = {}

    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: list[dict[str, Any]],
        previous_response_id: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        text: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> _ChatResponse:
        messages = self._build_messages(instructions, input, previous_response_id)
        chat_tools = [self._convert_tool(t) for t in tools] if tools else None
        response_format = self._convert_format(text) if text else None

        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if chat_tools:
            kwargs["tools"] = chat_tools
        if response_format:
            kwargs["response_format"] = response_format

        completion = self._client.chat.completions.create(**kwargs)
        return self._build_response(completion, messages)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        instructions: str,
        input_items: list[dict[str, Any]],
        previous_response_id: str | None,
    ) -> list[dict[str, Any]]:
        """Reconstruct the full message list for this turn."""

        is_tool_turn = bool(
            input_items
            and isinstance(input_items[0], dict)
            and input_items[0].get("type") == "function_call_output"
        )

        if previous_response_id and previous_response_id in self._history:
            base = self._history[previous_response_id]
            if is_tool_turn:
                tool_messages = [
                    {
                        "role": "tool",
                        "tool_call_id": item["call_id"],
                        "content": item["output"],
                    }
                    for item in input_items
                ]
                return base + tool_messages
            return base + input_items

        # Fresh conversation — prepend system instructions.
        system_msg: dict[str, Any] = {"role": "system", "content": instructions}
        return [system_msg, *input_items]

    def _build_response(
        self,
        completion: Any,
        messages: list[dict[str, Any]],
    ) -> _ChatResponse:
        choice = completion.choices[0]
        message = choice.message
        output_text: str = message.content or ""

        output: list[Any] = []
        tool_calls_for_history: list[dict[str, Any]] = []

        for tc in message.tool_calls or []:
            output.append(
                _FunctionCallItem(
                    call_id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                )
            )
            tool_calls_for_history.append(
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
            )

        assistant_msg: dict[str, Any] = {"role": "assistant", "content": output_text}
        if tool_calls_for_history:
            assistant_msg["tool_calls"] = tool_calls_for_history

        response_id = completion.id or str(uuid.uuid4())
        self._history[response_id] = messages + [assistant_msg]

        return _ChatResponse(
            response_id=response_id,
            output=output,
            output_text=output_text,
        )

    @staticmethod
    def _convert_tool(tool: dict[str, Any]) -> dict[str, Any]:
        """Convert a Responses API tool definition to Chat Completions format."""

        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
                "strict": tool.get("strict", True),
            },
        }

    @staticmethod
    def _convert_format(text: dict[str, Any]) -> dict[str, Any] | None:
        """Convert a Responses API text-format spec to Chat Completions response_format."""

        fmt = text.get("format", {})
        if fmt.get("type") == "json_schema":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": fmt.get("name", "response"),
                    "schema": fmt.get("schema", {}),
                    "strict": fmt.get("strict", True),
                },
            }
        return {"type": "json_object"}


class ChatCompletionsClient:
    """ResponsesClient-compatible wrapper for any Chat Completions provider."""

    def __init__(self, client: Any) -> None:
        self.responses = _ChatCompletionsResource(client)
