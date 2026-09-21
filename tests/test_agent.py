import pytest

from app.agent import Agent
from schemas import (
    AgentAction,
    AgentResponse,
    AllowedTool,
    RAGResult,
    RetrievedChunk,
    TicketStatus,
)

from pydantic import ValidationError


class FakeLLM:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0
        self.messages = []

    def generate(self, messages):
        self.messages.append(messages)

        response = self.responses[self.calls]
        self.calls += 1

        if isinstance(response, Exception):
            raise response

        return response


def make_agent(
    llm,
    retrieved_chunks=None,
    conversation_history=None,
    previous_tool_calls=None,
    previous_tool_results=None,
    tool_handlers=None,
):
    return Agent(
        system_prompt="You are a support agent.",
        user_query="I was charged twice.",
        retrieved_chunks=retrieved_chunks or [],
        conversation_history=conversation_history or [],
        previous_tool_calls=previous_tool_calls or [],
        previous_tool_results=previous_tool_results or [],
        llm=llm,
        tool_handlers=tool_handlers or {},
    )


# ---------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------

def test_prompt_assembly_preserves_system_prompt():
    llm = FakeLLM([
        AgentResponse(
            action=AgentAction.ANSWER,
            user_message="You will receive help.",
        )
    ])

    agent = make_agent(llm)

    agent.run()

    messages = llm.messages[0]

    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a support agent."


def test_prompt_assembly_includes_user_query():
    llm = FakeLLM([
        AgentResponse(
            action=AgentAction.ANSWER,
            user_message="You will receive help.",
        )
    ])

    agent = make_agent(llm)

    agent.run()

    messages = llm.messages[0]

    assert any(
        message["content"] == "I was charged twice."
        for message in messages
        if message["role"] == "user"
    )


def test_prompt_assembly_delimits_retrieved_chunks():
    chunk = RetrievedChunk(
        chunk_id="chunk-1",
        content="Duplicate charges can be refunded.",
        source="billing_faq",
    )

    llm = FakeLLM([
        AgentResponse(
            action=AgentAction.ANSWER,
            user_message="The charge can be reviewed.",
        )
    ])

    agent = make_agent(
        llm,
        retrieved_chunks=[chunk],
    )

    agent.run()

    messages = llm.messages[0]

    retrieved_message = next(
        message
        for message in messages
        if "<retrieved_context>" in message["content"]
    )

    content = retrieved_message["content"]

    assert "<retrieved_context>" in content
    assert "<retrieved_chunk>" in content
    assert "</retrieved_chunk>" in content
    assert "</retrieved_context>" in content
    assert "Duplicate charges can be refunded." in content


def test_prompt_assembly_delimits_tool_history():
    tool_call = AgentResponse(
        action=AgentAction.TOOL_CALL,
        tool=AllowedTool.SEARCH_KNOWLEDGE,
        tool_input={
            "query": "duplicate billing"
        },
    )

    tool_result = RAGResult(
        query="duplicate billing",
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                content="Duplicate billing policy.",
                source="billing_faq",
            )
        ],
    )

    llm = FakeLLM([
        AgentResponse(
            action=AgentAction.ANSWER,
            user_message="The issue can be reviewed.",
        )
    ])

    agent = make_agent(
        llm,
        previous_tool_calls=[tool_call],
        previous_tool_results=[tool_result],
    )

    agent.run()

    messages = llm.messages[0]

    tool_history_message = next(
        message
        for message in messages
        if "<tool_history>" in message["content"]
    )

    content = tool_history_message["content"]

    assert "<tool_history>" in content
    assert "<tool_call>" in content
    assert "</tool_call>" in content
    assert "<tool_result>" in content
    assert "</tool_result>" in content
    assert "</tool_history>" in content

    assert "duplicate billing" in content
    assert "Duplicate billing policy." in content


# ---------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------

def test_search_knowledge_dispatch():
    received = {}

    def search_handler(tool_input):
        received["input"] = tool_input
        return "search-result"

    llm = FakeLLM([])

    agent = make_agent(
        llm,
        tool_handlers={
            AllowedTool.SEARCH_KNOWLEDGE: search_handler,
        },
    )

    response = AgentResponse(
        action=AgentAction.TOOL_CALL,
        tool=AllowedTool.SEARCH_KNOWLEDGE,
        tool_input={
            "query": "duplicate billing"
        },
    )

    result = agent.call_tool(response)

    assert result == "search-result"
    assert received["input"].query == "duplicate billing"


def test_get_account_dispatch():
    received = {}

    def account_handler(tool_input):
        received["input"] = tool_input
        return {"account_status": "active"}

    llm = FakeLLM([])

    agent = make_agent(
        llm,
        tool_handlers={
            AllowedTool.GET_ACCOUNT: account_handler,
        },
    )

    response = AgentResponse(
        action=AgentAction.TOOL_CALL,
        tool=AllowedTool.GET_ACCOUNT,
        tool_input={},
    )

    result = agent.call_tool(response)

    assert result == {"account_status": "active"}
    assert received["input"].model_dump() == {}


def test_update_ticket_status_dispatch():
    received = {}

    def status_handler(tool_input):
        received["input"] = tool_input
        return "status-updated"

    llm = FakeLLM([])

    agent = make_agent(
        llm,
        tool_handlers={
            AllowedTool.UPDATE_TICKET_STATUS: status_handler,
        },
    )

    response = AgentResponse(
        action=AgentAction.TOOL_CALL,
        tool=AllowedTool.UPDATE_TICKET_STATUS,
        tool_input={
            "status": TicketStatus.RESOLVED.value
        },
    )

    result = agent.call_tool(response)

    assert result == "status-updated"
    assert received["input"].status == TicketStatus.RESOLVED


def test_invalid_tool_input_is_rejected():
    def search_handler(tool_input):
        return "should-not-run"

    llm = FakeLLM([])

    agent = make_agent(
        llm,
        tool_handlers={
            AllowedTool.SEARCH_KNOWLEDGE: search_handler,
        },
    )

    response = AgentResponse(
        action=AgentAction.TOOL_CALL,
        tool=AllowedTool.SEARCH_KNOWLEDGE,
        tool_input={
            "query": ""
        },
    )

    with pytest.raises(RuntimeError, match="Invalid input"):
        agent.call_tool(response)


def test_missing_tool_handler_is_rejected():
    llm = FakeLLM([])

    agent = make_agent(llm)

    response = AgentResponse(
        action=AgentAction.TOOL_CALL,
        tool=AllowedTool.SEARCH_KNOWLEDGE,
        tool_input={
            "query": "billing"
        },
    )

    with pytest.raises(
        RuntimeError,
        match="No handler registered for tool",
    ):
        agent.call_tool(response)

# ---------------------------------------------------------
# Structured output retry
# ---------------------------------------------------------
def test_invalid_structured_output_retries_once():
    valid_response = AgentResponse(
        action=AgentAction.ANSWER,
        user_message="Your request has been received.",
    )

    class RetryLLM:
        def __init__(self):
            self.calls = 0

        def generate(self, messages):
            self.calls += 1

            if self.calls == 1:
                raise ValidationError.from_exception_data(
                    "AgentResponse",
                    [],
                )

            return valid_response

    llm = RetryLLM()

    agent = make_agent(llm)

    result = agent.run()

    assert result == valid_response
    assert llm.calls == 2

def test_invalid_structured_output_twice_fails():
    class AlwaysInvalidLLM:
        def __init__(self):
            self.calls = 0

        def generate(self, messages):
            self.calls += 1

            raise ValidationError.from_exception_data(
                "AgentResponse",
                [],
            )

    llm = AlwaysInvalidLLM()

    agent = make_agent(llm)

    with pytest.raises(
        RuntimeError,
        match="invalid structured output after one retry",
    ):
        agent.run()

    assert llm.calls == 2


def test_agent_executes_tool_on_iteration_five_then_stops():
    calls = []

    def search_handler(tool_input):
        calls.append(tool_input.query)
        return "final-tool-result"

    tool_response = AgentResponse(
        action=AgentAction.TOOL_CALL,
        tool=AllowedTool.SEARCH_KNOWLEDGE,
        tool_input={
            "query": "billing"
        },
    )

    llm = FakeLLM([
        tool_response,
        tool_response,
        tool_response,
        tool_response,
        tool_response,
    ])

    agent = make_agent(
        llm,
        tool_handlers={
            AllowedTool.SEARCH_KNOWLEDGE: search_handler,
        },
    )

    result = agent.run()

    assert result == "final-tool-result"

    assert len(calls) == 5
    assert llm.calls == 5
    assert agent.iteration == 5
    assert agent.tool_calls == 5


def test_agent_stops_when_tool_call_limit_is_reached():
    calls = []

    def search_handler(tool_input):
        calls.append(tool_input.query)
        return "result"

    tool_response = AgentResponse(
        action=AgentAction.TOOL_CALL,
        tool=AllowedTool.SEARCH_KNOWLEDGE,
        tool_input={
            "query": "billing"
        },
    )

    llm = FakeLLM([
        tool_response,
        tool_response,
        tool_response,
        tool_response,
        tool_response,
        tool_response,
    ])

    agent = make_agent(
        llm,
        tool_handlers={
            AllowedTool.SEARCH_KNOWLEDGE: search_handler,
        },
    )

    agent.max_tool_calls = 5

    result = agent.run()

    assert result == "result"
    assert len(calls) == 5
    assert llm.calls == 5
