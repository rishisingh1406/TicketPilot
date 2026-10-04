import time

from typing import Any

from app.agent import Agent, search_knowledge

from app.retrieval import KnowledgeRetriever

from app.ticket_service import SYSTEM_PROMPT

from schemas import AgentAction, AgentResponse, AllowedTool

from eval.citation_judge import CitationFaithfulnessJudge

from eval.metrics import evaluate_citation

from eval.schemas import (
    CitationFaithfulnessResult,
    EvaluationResult,
)


INPUT_COST_PER_MILLION = 0.80
OUTPUT_COST_PER_MILLION = 4.00


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Calculate LLM cost.

    Pricing:
    - Input: $0.80 / 1M tokens
    - Output: $4.00 / 1M tokens
    """
    return (
        prompt_tokens / 1_000_000 * INPUT_COST_PER_MILLION
        + completion_tokens / 1_000_000 * OUTPUT_COST_PER_MILLION
    )


def evaluate_case(
    case: dict[str, Any],
    llm,
    db,
    retriever: KnowledgeRetriever,
    citation_judge: CitationFaithfulnessJudge,
) -> EvaluationResult:
    """
    Evaluate one golden-set case against the TicketPilot agent.

    Production-agent execution and citation-judge execution are
    intentionally isolated so that a judge failure cannot erase
    a valid production-agent result.
    """
    expected = case["expected"]

    expected_action = AgentAction(
        expected["action"]
    )

    expected_sources = expected.get(
        "expected_sources",
        [],
    )

    citation_required = expected.get(
        "citation_required",
        False,
    )

    # ------------------------------------------------------------
    # Fresh usage accounting for this case
    # ------------------------------------------------------------

    llm.reset_usage()
    citation_judge.reset_usage()

    # ------------------------------------------------------------
    # Production-agent execution
    # ------------------------------------------------------------

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

    except Exception as error:
        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        # Production-agent usage may exist even when the agent fails.
        llm_calls = llm.call_count
        prompt_tokens = llm.total_prompt_tokens
        completion_tokens = llm.total_completion_tokens
        total_tokens = llm.total_tokens

        cost_usd = calculate_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return EvaluationResult(
            case_id=case["id"],
            expected_action=expected_action,
            actual_action=None,
            structured_output_valid=False,
            expected_sources=expected_sources,
            actual_sources=[],
            citation_correct=None,
            citation_faithfulness=None,
            citation_judge_reason=None,
            citation_judge_unsupported_claims=[],
            latency_ms=latency_ms,

            # Production-agent usage
            llm_calls=llm_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,

            # Judge usage
            judge_llm_calls=0,
            judge_prompt_tokens=0,
            judge_completion_tokens=0,
            judge_total_tokens=0,
            judge_cost_usd=0.0,

            production_error=(
                f"{type(error).__name__}: {error}"
            ),
            citation_judge_error=None,
        )

    # ------------------------------------------------------------
    # Production-agent latency and usage
    # ------------------------------------------------------------

    latency_ms = (
        time.perf_counter() - start_time
    ) * 1000

    llm_calls = llm.call_count
    prompt_tokens = llm.total_prompt_tokens
    completion_tokens = llm.total_completion_tokens
    total_tokens = llm.total_tokens

    cost_usd = calculate_cost(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    # ------------------------------------------------------------
    # Validate final production-agent result
    # ------------------------------------------------------------

    if not isinstance(result, AgentResponse):
        return EvaluationResult(
            case_id=case["id"],
            expected_action=expected_action,
            actual_action=None,
            structured_output_valid=False,
            expected_sources=expected_sources,
            actual_sources=[],
            citation_correct=None,
            citation_faithfulness=None,
            citation_judge_reason=None,
            citation_judge_unsupported_claims=[],
            latency_ms=latency_ms,

            # Production-agent usage
            llm_calls=llm_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,

            # Judge was never called
            judge_llm_calls=0,
            judge_prompt_tokens=0,
            judge_completion_tokens=0,
            judge_total_tokens=0,
            judge_cost_usd=0.0,

            production_error=(
                "Agent returned an invalid final result: "
                f"{type(result).__name__}"
            ),
            citation_judge_error=None,
        )

    # ------------------------------------------------------------
    # Extract retrieved evidence
    # ------------------------------------------------------------

    actual_sources: list[str] = []
    retrieved_sources: list[dict[str, Any]] = []

    if result.retrieved_context is not None:
        for chunk in result.retrieved_context.chunks:
            source_name = chunk.source

            actual_sources.append(
                source_name
            )

            chunk_content = getattr(
                chunk,
                "content",
                None,
            )

            if chunk_content is None:
                chunk_content = getattr(
                    chunk,
                    "chunk_text",
                    "",
                )

            retrieved_sources.append(
                {
                    "source": source_name,
                    "content": chunk_content,
                }
            )

        actual_sources = list(
            dict.fromkeys(actual_sources)
        )

    # ------------------------------------------------------------
    # Citation correctness
    # ------------------------------------------------------------

    citation_correct = evaluate_citation(
        expected_sources=expected_sources,
        actual_sources=actual_sources,
        citation_required=citation_required,
    )

    # ------------------------------------------------------------
    # Citation-faithfulness judge
    #
    # IMPORTANT:
    # Judge failures are isolated from the production result.
    # ------------------------------------------------------------

    citation_faithfulness: CitationFaithfulnessResult | None = None
    citation_judge_error: str | None = None

    if citation_required:
        try:
            citation_faithfulness = citation_judge.evaluate(
                user_question=case["user_message"],
                generated_answer=result.user_message or "",
                retrieved_sources=retrieved_sources,
                expected_sources=expected_sources,
            )

        except Exception as error:
            citation_judge_error = (
                f"{type(error).__name__}: {error}"
            )

    # ------------------------------------------------------------
    # Judge usage
    # ------------------------------------------------------------

    judge_llm_calls = citation_judge.call_count

    judge_prompt_tokens = (
        citation_judge.total_prompt_tokens
    )

    judge_completion_tokens = (
        citation_judge.total_completion_tokens
    )

    judge_total_tokens = (
        citation_judge.total_tokens
    )

    judge_cost_usd = calculate_cost(
        prompt_tokens=judge_prompt_tokens,
        completion_tokens=judge_completion_tokens,
    )

    # ------------------------------------------------------------
    # Final evaluation result
    #
    # A judge failure does NOT affect:
    # - actual_action
    # - structured_output_valid
    # - production latency
    # - production token usage
    # - production cost
    #
    # structured_output_valid comes from the production Agent.
    # The Agent marks it False if any structured-output failure
    # occurs, even if the retry succeeds or the agent escalates.
    # ------------------------------------------------------------

    return EvaluationResult(
        case_id=case["id"],
        expected_action=expected_action,
        actual_action=result.action,

        # IMPORTANT:
        # Do not hardcode this to True.
        structured_output_valid=agent.structured_output_valid,

        expected_sources=expected_sources,
        actual_sources=actual_sources,
        citation_correct=citation_correct,

        citation_faithfulness=(
            citation_faithfulness.verdict
            if citation_faithfulness
            else None
        ),

        citation_judge_reason=(
            citation_faithfulness.reason
            if citation_faithfulness
            else None
        ),

        citation_judge_unsupported_claims=(
            citation_faithfulness.unsupported_claims
            if citation_faithfulness
            else []
        ),

        latency_ms=latency_ms,

        # Production-agent usage
        llm_calls=llm_calls,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,

        # Citation-judge usage
        judge_llm_calls=judge_llm_calls,
        judge_prompt_tokens=judge_prompt_tokens,
        judge_completion_tokens=judge_completion_tokens,
        judge_total_tokens=judge_total_tokens,
        judge_cost_usd=judge_cost_usd,

        production_error=None,
        citation_judge_error=citation_judge_error,
    )
