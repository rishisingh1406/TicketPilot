from pydantic import BaseModel, Field

from schemas import AgentAction


class EvaluationResult(BaseModel):
    """
    Result of evaluating one golden-set case.
    """

    case_id: str = Field(min_length=1)

    expected_action: AgentAction

    actual_action: AgentAction | None = None

    structured_output_valid: bool

    expected_sources: list[str] = Field(
        default_factory=list
    )

    actual_sources: list[str] = Field(
        default_factory=list
    )

    citation_correct: bool | None = None

    latency_ms: float = Field(ge=0)

    error: str | None = None