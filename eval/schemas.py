from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from schemas import AgentAction


class CitationFaithfulnessVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"

class CitationFaithfulnessResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    verdict: CitationFaithfulnessVerdict

    reason: str = Field(
        min_length=1
    )

    unsupported_claims: list[str]


class EvaluationResult(BaseModel):
    """
    Result of evaluating one golden-set case.

    Production-agent failures and evaluation-infrastructure
    failures are tracked separately so that a judge failure
    cannot be mistaken for an agent failure.
    """

    # ------------------------------------------------------------
    # Case identity
    # ------------------------------------------------------------

    case_id: str = Field(
        min_length=1
    )

    expected_action: AgentAction

    # ------------------------------------------------------------
    # Production agent result
    # ------------------------------------------------------------

    actual_action: AgentAction | None = None

    structured_output_valid: bool

    # ------------------------------------------------------------
    # Retrieval / citation evidence
    # ------------------------------------------------------------

    expected_sources: list[str] = Field(
        default_factory=list
    )

    actual_sources: list[str] = Field(
        default_factory=list
    )

    # ------------------------------------------------------------
    # Citation correctness
    # ------------------------------------------------------------

    citation_correct: bool | None = None

    # ------------------------------------------------------------
    # Citation faithfulness
    # ------------------------------------------------------------

    citation_faithfulness: CitationFaithfulnessVerdict | None = None

    citation_judge_reason: str | None = None

    citation_judge_unsupported_claims: list[str] = Field(
        default_factory=list
    )

    # ------------------------------------------------------------
    # Production agent performance
    # ------------------------------------------------------------

    latency_ms: float = Field(
        ge=0
    )

    # ------------------------------------------------------------
    # Production agent LLM usage
    # ------------------------------------------------------------

    llm_calls: int = Field(
        ge=0
    )

    prompt_tokens: int = Field(
        ge=0
    )

    completion_tokens: int = Field(
        ge=0
    )

    total_tokens: int = Field(
        ge=0
    )

    # ------------------------------------------------------------
    # Production agent cost
    # ------------------------------------------------------------

    cost_usd: float = Field(
        ge=0
    )

    # ------------------------------------------------------------
    # Citation judge LLM usage
    # ------------------------------------------------------------

    judge_llm_calls: int = Field(
        ge=0
    )

    judge_prompt_tokens: int = Field(
        ge=0
    )

    judge_completion_tokens: int = Field(
        ge=0
    )

    judge_total_tokens: int = Field(
        ge=0
    )

    # ------------------------------------------------------------
    # Citation judge cost
    # ------------------------------------------------------------

    judge_cost_usd: float = Field(
        ge=0
    )

    # ------------------------------------------------------------
    # Failure classification
    # ------------------------------------------------------------

    # Failure in the production agent itself.
    production_error: str | None = None

    # Failure in the evaluation infrastructure,
    # specifically the citation-faithfulness judge.
    citation_judge_error: str | None = None
