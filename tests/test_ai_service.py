"""Tests for the OpenAI-independent AI service orchestration layer."""

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from app.ai.contracts import ConversationMessage, ConversationState, StructuredOutputSpec, ToolDefinition
from app.ai.service import AIService
from app.ai.tools import ToolRegistry


@dataclass
class _FakeResponse:
    id: str
    output_text: str
    output: list[object]


class _FakeResponses:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.requests: list[dict[str, Any]] = []

    def create(self, **request: Any) -> _FakeResponse:
        self.requests.append(request)
        return self._response


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.responses = _FakeResponses(response)


def test_structured_command_uses_responses_text_format() -> None:
    """The service maps a structured-output request to the Responses API shape."""

    client = _FakeClient(_FakeResponse(id="resp_1", output_text='{"intent":"review"}', output=[]))
    result = AIService(client, "test-model").command(
        "Review overdue invoices",
        business_context="A demo business",
        structured_output=StructuredOutputSpec(
            name="command_result",
            schema={"type": "object", "properties": {"intent": {"type": "string"}}},
        ),
    )

    request = client.responses.requests[0]
    assert request["text"]["format"]["type"] == "json_schema"
    assert result.structured_output == {"intent": "review"}
    assert result.conversation.previous_response_id == "resp_1"


def test_continued_conversation_does_not_replay_local_history() -> None:
    """A prior Responses ID is used as the server-side conversation continuation."""

    client = _FakeClient(_FakeResponse(id="resp_2", output_text="Done", output=[]))
    state = ConversationState(
        messages=(ConversationMessage(role="user", content="Earlier request"),),
        previous_response_id="resp_1",
    )
    AIService(client, "test-model").command("Follow up", conversation=state)

    request = client.responses.requests[0]
    assert request["previous_response_id"] == "resp_1"
    assert request["input"] == [{"role": "user", "content": "Follow up"}]


def test_tool_execution_returns_structured_audit_entries() -> None:
    """Every executed model action is returned and sent back as JSON tool output."""

    first = _FakeResponse(
        id="resp_1",
        output_text="",
        output=[
            SimpleNamespace(
                type="function_call",
                call_id="call_1",
                name="create_reminder",
                arguments=(
                    '{"title":"Call Ada","reason":"The user asked for a follow-up."}'
                ),
            )
        ],
    )
    second = _FakeResponse(id="resp_2", output_text="Reminder created.", output=[])

    class SequenceResponses:
        def __init__(self) -> None:
            self.requests: list[dict[str, Any]] = []
            self._responses = [first, second]

        def create(self, **request: Any) -> _FakeResponse:
            self.requests.append(request)
            return self._responses.pop(0)

    registry = ToolRegistry()
    registry.register(
        ToolDefinition("create_reminder", "Create a reminder.", {"type": "object"}),
        lambda arguments: {
            "status": "completed",
            "id": "rem_1",
            "title": arguments["title"],
        },
    )
    client = SimpleNamespace(responses=SequenceResponses())

    result = AIService(client, "test-model", tool_registry=registry).command(
        "Remind me to call Ada", execute_tools=True
    )

    assert result.text == "Reminder created."
    assert result.actions[0].tool_name == "create_reminder"
    assert result.actions[0].reason == "The user asked for a follow-up."
    assert result.actions[0].status == "completed"
    assert client.responses.requests[0]["tools"][0]["name"] == "create_reminder"
    output = client.responses.requests[1]["input"][0]["output"]
    assert json.loads(output)["id"] == "rem_1"
