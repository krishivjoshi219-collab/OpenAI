"""Tests for the OpenAI-independent AI service orchestration layer."""

from dataclasses import dataclass
from typing import Any

from app.ai.contracts import ConversationMessage, ConversationState, StructuredOutputSpec
from app.ai.service import AIService


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
