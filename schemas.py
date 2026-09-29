from datetime import datetime

from enum import Enum

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================
# Schema for incoming request
# ============================================================


class CreateTicketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(
        ...,
        description="The ID of the user making the request",
    )

    message: str = Field(
        ...,
        min_length=1,
        description="The message from the user",
    )


# ============================================================
# Ticket Lifecycle
# ============================================================


class TicketStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ESCALATED_TO_SUPPORT = "ESCALATED_TO_SUPPORT"
    RESOLVED = "RESOLVED"
    

class TicketDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: TicketStatus


class Ticket(BaseModel):
    """
    System-of-record representation of a support ticket.

    A ticket is created for every user query.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    original_user_message: str = Field(min_length=1)
    status: TicketStatus = TicketStatus.CREATED
    final_answer: str | None = None
    created_at: datetime
    updated_at: datetime


# ============================================================
# Integrity Gate
# ============================================================


class IntegrityDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class IntegrityCheckResult(BaseModel):
    """
    Result produced by an Integrity Gate.

    Used both before agent execution and after tool execution.
    """

    model_config = ConfigDict(extra="forbid")

    decision: IntegrityDecision
    reason: str | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> "IntegrityCheckResult":
        if self.decision == IntegrityDecision.BLOCK and not self.reason:
            raise ValueError(
                "reason is required when decision is BLOCK"
            )

        if self.decision == IntegrityDecision.ALLOW and self.reason:
            raise ValueError(
                "reason must be null when decision is ALLOW"
            )

        return self


# ============================================================
# Handleability Classification
# ============================================================


class Handleability(str, Enum):
    HANDLE = "HANDLE"
    SUPPORT = "SUPPORT"


class HandleabilityResult(BaseModel):
    """
    Result of determining whether the ticket can be handled
    using the approved company manual.
    """

    model_config = ConfigDict(extra="forbid")

    decision: Handleability
    reason: str | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> "HandleabilityResult":
        if self.decision == Handleability.SUPPORT and not self.reason:
            raise ValueError(
                "reason is required when decision is SUPPORT"
            )

        return self


# ============================================================
# RAG
# ============================================================


class RetrievedChunk(BaseModel):
    """
    A single piece of approved manual content returned by RAG.
    """

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)

    # Metadata used to distinguish newer/older manual content.
    timestamp: datetime | None = None
    is_current: bool | None = None

    # Lower cosine distance means higher similarity.
    distance: float


class RAGResult(BaseModel):
    """
    Structured result returned by the RAG tool.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    chunks: list[RetrievedChunk]


# ============================================================
# Agent Actions
# ============================================================


class AgentAction(str, Enum):
    TOOL_CALL = "TOOL_CALL"
    ANSWER = "ANSWER"
    ESCALATE = "ESCALATE"


class AllowedTool(str, Enum):
    SEARCH_KNOWLEDGE = "SEARCH_KNOWLEDGE"
    GET_ACCOUNT = "GET_ACCOUNT"
    UPDATE_TICKET_STATUS = "UPDATE_TICKET_STATUS"


# ============================================================
# Human Review Actions
# ============================================================


class ReviewerAction(str, Enum):
    """
    Business outcomes available to a human reviewer.

    RESOLVE:
        Accept the existing AI answer without modification.

    EDIT_AND_RESOLVE:
        Modify the AI answer and resolve the ticket.

    TAKE_OVER:
        The reviewer cannot safely resolve the ticket and
        transfers ownership to human support.
    """

    RESOLVE = "RESOLVE"
    EDIT_AND_RESOLVE = "EDIT_AND_RESOLVE"
    TAKE_OVER = "TAKE_OVER"


class ReviewerActionRequest(BaseModel):
    """
    Request submitted by the human reviewer.

    The required fields depend on the selected action.
    """

    model_config = ConfigDict(extra="forbid")

    action: ReviewerAction

    reviewer_identity: str = Field(
        min_length=1,
        description="Identity of the human reviewer",
    )

    edited_answer: str | None = Field(
        default=None,
        description="Human-modified answer used for EDIT_AND_RESOLVE",
    )

    reason: str | None = Field(
        default=None,
        description="Reason required when taking over the ticket",
    )

    @model_validator(mode="after")
    def validate_action_contract(self) -> "ReviewerActionRequest":

        # ----------------------------------------------------
        # RESOLVE
        # ----------------------------------------------------

        if self.action == ReviewerAction.RESOLVE:

            if self.edited_answer is not None:
                raise ValueError(
                    "edited_answer must be null for RESOLVE"
                )

            if self.reason is not None:
                raise ValueError(
                    "reason must be null for RESOLVE"
                )

        # ----------------------------------------------------
        # EDIT_AND_RESOLVE
        # ----------------------------------------------------

        elif self.action == ReviewerAction.EDIT_AND_RESOLVE:

            if not self.edited_answer or not self.edited_answer.strip():
                raise ValueError(
                    "edited_answer is required for EDIT_AND_RESOLVE"
                )

            if self.reason is not None:
                raise ValueError(
                    "reason must be null for EDIT_AND_RESOLVE"
                )

        # ----------------------------------------------------
        # TAKE_OVER
        # ----------------------------------------------------

        elif self.action == ReviewerAction.TAKE_OVER:

            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "reason is required for TAKE_OVER"
                )

            if self.edited_answer is not None:
                raise ValueError(
                    "edited_answer must be null for TAKE_OVER"
                )

        return self


# ============================================================
# Review Item
# ============================================================


class ReviewTicket(BaseModel):
    """
    Ticket information displayed to the human reviewer.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    original_user_message: str = Field(min_length=1)
    conversation: list[dict[str, Any]] = Field(default_factory=list)
    status: TicketStatus


class ReviewAgentResult(BaseModel):
    """
    Agent output displayed to the human reviewer.
    """

    model_config = ConfigDict(extra="forbid")

    proposed_answer: str | None = None
    decision: AgentAction
    reason: str | None = None


class ReviewEvidence(BaseModel):
    """
    Evidence used by the agent while producing its result.
    """

    model_config = ConfigDict(extra="forbid")

    retrieved_chunks: list[RetrievedChunk] = Field(
        default_factory=list
    )

    sources: list[str] = Field(
        default_factory=list
    )


class ReviewValidation(BaseModel):
    """
    Answer validation information displayed to the reviewer.
    """

    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)
    reason: str | None = None


class ReviewItem(BaseModel):
    """
    Complete review context presented to the human reviewer.

    This is a read model for the reviewer interface.
    It does not own business logic.
    """

    model_config = ConfigDict(extra="forbid")

    ticket: ReviewTicket
    agent_result: ReviewAgentResult
    evidence: ReviewEvidence
    tool_activity: list[dict[str, Any]] = Field(
        default_factory=list
    )
    validation: ReviewValidation | None = None
    escalation_context: str | None = None


# ============================================================
# Tool Input Schemas
# ============================================================


class SearchKnowledgeInput(BaseModel):
    """
    Input contract for the SEARCH_KNOWLEDGE tool.

    The LLM provides the search query.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=1,
        description="The knowledge-base search query",
    )


class GetAccountInput(BaseModel):
    """
    Input contract for the GET_ACCOUNT tool.

    No user ID is accepted from the LLM.
    The application owns the trusted user context.
    """

    model_config = ConfigDict(extra="forbid")


class UpdateTicketStatusInput(BaseModel):
    """
    Input contract for the UPDATE_TICKET_STATUS tool.

    The LLM can request the desired status.
    The application owns the trusted ticket context.
    """

    model_config = ConfigDict(extra="forbid")

    status: TicketStatus


# ============================================================
# Tool → Input Schema Mapping
# ============================================================


TOOL_INPUT_MODELS = {
    AllowedTool.SEARCH_KNOWLEDGE: SearchKnowledgeInput,
    AllowedTool.GET_ACCOUNT: GetAccountInput,
    AllowedTool.UPDATE_TICKET_STATUS: UpdateTicketStatusInput,
}


# ============================================================
# Agent Response
# ============================================================


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: AgentAction
    tool: AllowedTool | None = None
    tool_input: dict[str, Any] | None = None
    user_message: str | None = None
    support_message: str | None = None
    retrieved_context: RAGResult | None = None

    @model_validator(mode="after")
    def validate_action_contract(self) -> "AgentResponse":
        
        # ----------------------------------------------------
        # TOOL_CALL
        # ----------------------------------------------------

        if self.action == AgentAction.TOOL_CALL:

            if self.tool is None:
                raise ValueError(
                    "TOOL_CALL requires a tool"
                )

            if self.tool_input is None:
                raise ValueError(
                    "TOOL_CALL requires tool_input"
                )

            if self.user_message is not None:
                raise ValueError(
                    "TOOL_CALL requires user_message to be null"
                )

            if self.support_message is not None:
                raise ValueError(
                    "TOOL_CALL requires support_message to be null"
                )

        # ----------------------------------------------------
        # ANSWER
        # ----------------------------------------------------

        elif self.action == AgentAction.ANSWER:

            if self.tool is not None:
                raise ValueError(
                    "ANSWER requires tool to be null"
                )

            if self.tool_input is not None:
                raise ValueError(
                    "ANSWER requires tool_input to be null"
                )

            if not self.user_message:
                raise ValueError(
                    "ANSWER requires user_message"
                )

            if self.support_message is not None:
                raise ValueError(
                    "ANSWER requires support_message to be null"
                )

        # ----------------------------------------------------
        # ESCALATE
        # ----------------------------------------------------

        elif self.action == AgentAction.ESCALATE:

            if self.tool is not None:
                raise ValueError(
                    "ESCALATE requires tool to be null"
                )

            if self.tool_input is not None:
                raise ValueError(
                    "ESCALATE requires tool_input to be null"
                )

            if not self.user_message:
                raise ValueError(
                    "ESCALATE requires user_message"
                )

            if not self.support_message:
                raise ValueError(
                    "ESCALATE requires support_message"
                )

        return self


# ============================================================
# Answer Validation
# ============================================================


class AnswerValidationResult(BaseModel):
    """
    Semantic validation result for a candidate answer.

    The validator checks whether the answer:

    1. Addresses the user's query.
    2. Is supported by retrieved approved manual content.
    """

    model_config = ConfigDict(extra="forbid")

    valid: bool
    reason: str | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> "AnswerValidationResult":

        if not self.valid and not self.reason:
            raise ValueError(
                "reason is required when answer is invalid"
            )

        if self.valid and self.reason is not None:
            raise ValueError(
                "reason must be null when answer is valid"
            )

        return self


# ============================================================
# Support Handoff
# ============================================================


class SupportHandoff(BaseModel):
    """
    Information sent to the human support team when the agent
    cannot safely resolve the ticket.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    original_user_message: str = Field(min_length=1)
    support_message: str = Field(min_length=1)


# ============================================================
# Persistence
# ============================================================


class TicketResolution(BaseModel):
    """
    Data persisted when a ticket is successfully resolved.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    original_user_message: str = Field(min_length=1)
    final_answer: str = Field(min_length=1)
    status: TicketStatus
    resolved_at: datetime


# ============================================================
# Agent Execution State
# ============================================================


class ExecutionState(BaseModel):
    """
    Runtime state owned by the Agent Orchestrator.

    This is execution state, not persistent ticket state.
    """

    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(ge=0)
    max_iterations: int = Field(gt=0)

    schema_validation_attempts: int = Field(ge=0)
    max_schema_validation_retries: int = Field(ge=0)

    semantic_validation_attempts: int = Field(ge=0)
    max_semantic_validation_retries: int = Field(ge=0)

    previous_tool_result: RAGResult | None = None


# ============================================================
# Client Response
# ============================================================


class ClientResponse(BaseModel):
    """
    Response returned by the API to the user.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(min_length=1)
    status: TicketStatus
    message: str = Field(min_length=1)
