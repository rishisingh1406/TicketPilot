import time
from typing import Any

from app.agent import Agent, search_knowledge
from app.retrieval import KnowledgeRetriever
from app.ticket_service import SYSTEM_PROMPT
from schemas import AgentAction, AgentResponse, AllowedTool

from eval.metrics import evaluate_citation
from eval.schemas import EvaluationResult


def evaluate_case(
    case: dict[str, Any],
    llm,
    db,
    retriever: KnowledgeRetriever,
) -> EvaluationResult:
    """
    Evaluate one golden-set case against the TicketPilot agent.
    """

    expected = case["expected"]

    expected_action = AgentAction(expected["action"])

    expected_sources = expected.get(
        "expected_sources",
        [],
    )

    citation_required = expected.get(
        "citation_required",
        False,
    )

    start_time = time.perf_counter()

    try:
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            user_query=case["user_message"],
            retrieved_chunks=[],
            conversation_history=[],
            previous_tool_calls=[],
            previous_tool_results=[],
            llm=llm,
            db=db,
            retriever=retriever,
            tool_handlers={
                AllowedTool.SEARCH_KNOWLEDGE: search_knowledge,
            },
        )

        result = agent.run()

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        # Agent.run() is expected to return AgentResponse.
        if not isinstance(result, AgentResponse):
            return EvaluationResult(
                case_id=case["id"],
                expected_action=expected_action,
                actual_action=None,
                structured_output_valid=False,
                expected_sources=expected_sources,
                actual_sources=[],
                citation_correct=None,
                latency_ms=latency_ms,
                error=(
                    "Agent returned an invalid final result: "
                    f"{type(result).__name__}"
                ),
            )

        actual_sources = []

        if result.retrieved_context is not None:
            actual_sources = list(
                dict.fromkeys(
                    chunk.source
                    for chunk in result.retrieved_context.chunks
                )
            )

        citation_correct = evaluate_citation(
            expected_sources=expected_sources,
            actual_sources=actual_sources,
            citation_required=citation_required,
        )

        return EvaluationResult(
            case_id=case["id"],
            expected_action=expected_action,
            actual_action=result.action,
            structured_output_valid=True,
            expected_sources=expected_sources,
            actual_sources=actual_sources,
            citation_correct=citation_correct,
            latency_ms=latency_ms,
            error=None,
        )

    except Exception as error:

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        return EvaluationResult(
            case_id=case["id"],
            expected_action=expected_action,
            actual_action=None,
            structured_output_valid=False,
            expected_sources=expected_sources,
            actual_sources=[],
            citation_correct=None,
            latency_ms=latency_ms,
            error=f"{type(error).__name__}: {error}",
        )