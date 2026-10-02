import logging

from sqlalchemy.orm import Session

from app.agent import Agent, search_knowledge
from app.retrieval import KnowledgeRetriever

from models import (
    Audit,
    Draft,
    Review,
    Ticket,
    AgentDecision,
)

from schemas import (
    AgentAction,
    AgentResponse,
    AllowedTool,
    ReviewerAction,
    TicketStatus,
    ReviewItem,
    ReviewTicket,
    ReviewAgentResult,
    ReviewEvidence,
    ReviewValidation,
    RAGResult,
)


logger = logging.getLogger(__name__)



SYSTEM_PROMPT = """
You are TicketPilot, a SaaS support agent.

Your job is to answer customer support tickets using reliable
information from the available knowledge base.

AVAILABLE TOOL

The only knowledge-base tool available to you is:

SEARCH_KNOWLEDGE

Purpose:
Search the approved TicketPilot knowledge base for relevant
documentation.

The application executes the tool. You only request the tool call.

TOOL INPUT

For SEARCH_KNOWLEDGE, the application expects:

{
    "query": "<search query>"
}

IMPORTANT TOOL CONTRACT

When requesting a tool call:

- The "action" field MUST be "TOOL_CALL".
- The "tool" field MUST be exactly:
  "SEARCH_KNOWLEDGE"
- The "query" field MUST contain the search query.
- The "status" field MUST be an empty string.
- The "user_message" field MUST be an empty string.
- The "support_message" field MUST be an empty string.

Do not generate additional tool parameters.

Do not use alternative tool names such as:
- "search"
- "get_search_results"
- "search_knowledge_base"
- or any other tool name.

Do not generate tool execution status values such as:
- "PENDING"
- "PROCESSING"
- "FINISHED"
- "REQUESTING_TOOL"
- "COMPLETED"

Do not generate progress messages such as:
- "Let me check..."
- "Please hold on..."
- "Searching..."
- "Checking the knowledge base..."

The application owns tool execution and execution status.

ACTION CONTRACT

When action is "TOOL_CALL":

- tool = "SEARCH_KNOWLEDGE"
- query = the search query
- status = ""
- user_message = ""
- support_message = ""

When action is "ANSWER":

- tool = ""
- query = ""
- status = ""
- user_message = the final customer-facing answer
- support_message = ""

When action is "ESCALATE":

- tool = ""
- query = ""
- status = ""
- user_message = the customer-facing fallback message
- support_message = the explanation for human support

ANSWERING

Use SEARCH_KNOWLEDGE before answering when the answer depends
on information in the knowledge base.

Only answer when the retrieved information is sufficient to
support the answer.

After a TOOL_CALL, the application will execute the requested
tool and provide the tool result to you.

Use the returned tool result as the source of truth for the
next decision.

If the available information is insufficient, conflicting,
outdated, or unreliable, escalate the ticket to human support.

Do not invent policies, account information, or facts.

CITATIONS

When answering using knowledge-base information:

- Base the answer on the retrieved knowledge.
- Preserve the relevant source information.
- Do not claim information that is not supported by the retrieved
  knowledge.
- If the retrieved knowledge does not support a reliable answer,
  escalate instead of guessing.

FINAL RESPONSE

For an ANSWER, provide a clear and concise customer-facing
response.

For an ESCALATE, provide:
- a short customer-facing fallback in "user_message"
- a useful explanation for the human support team in
  "support_message"

Never include tool instructions, internal reasoning, or
execution-status messages in the customer-facing response.
"""



def create_ticket(
    db: Session,
    user_id: int,
    message: str,
) -> Ticket:
    new_ticket = Ticket(
        user_id=str(user_id),
        user_message=message,
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return new_ticket


def get_tickets(db: Session):
    return db.query(Ticket).all()


def generate_ticket_draft(
    db: Session,
    ticket_id: int,
    llm,
    retriever: KnowledgeRetriever,
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .first()
    )

    if ticket is None:
        return None

    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        user_query=ticket.user_message,
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

    agent_response: AgentResponse = agent.run()

    # ---------------------------------------------------------
    # Successful agent answer
    # ---------------------------------------------------------

    if agent_response.action == AgentAction.ANSWER:
        evidence = ""

        if agent_response.retrieved_context is not None:
            evidence = (
                agent_response.retrieved_context.model_dump_json()
            )

        draft = Draft(
            ticket_id=ticket.ticket_id,
            generated_answer=agent_response.user_message,
            evidence=evidence,
            model_metadata="",
        )

        # A successful agent answer completes the ticket lifecycle.
        ticket.status = TicketStatus.RESOLVED

        # Draft persistence and lifecycle transition must succeed
        # together as one database transaction.
        db.add(draft)

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(draft)

        return draft

    # ---------------------------------------------------------
    # Agent escalation
    # ---------------------------------------------------------

    if agent_response.action == AgentAction.ESCALATE:
        return escalate_ticket(
            db=db,
            ticket_id=ticket_id,
            agent_response=agent_response,
        )

    return None


def escalate_ticket(
    db: Session,
    ticket_id: int,
    agent_response: AgentResponse,
) -> Review:
    """
    Persist an agent escalation and transfer the ticket to human review.

    The agent's proposed answer is stored as a Draft.
    The escalation reason is stored as a Review.
    Ticket state, Draft, and Review are committed atomically.
    """

    if agent_response.action != AgentAction.ESCALATE:
        raise ValueError(
            "escalate_ticket requires an ESCALATE agent response"
        )

    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .first()
    )

    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} not found")

    if not agent_response.user_message:
        raise ValueError(
            "Escalation requires a proposed user_message"
        )

    if not agent_response.support_message:
        raise ValueError(
            "Escalation requires a support_message/reason"
        )

    # ---------------------------------------------------------
    # 1. Update durable ticket state
    # ---------------------------------------------------------

    ticket.status = TicketStatus.REVIEW_REQUIRED

    # ---------------------------------------------------------
    # 2. Persist the agent's proposed answer
    # ---------------------------------------------------------

    evidence = ""

    if agent_response.retrieved_context is not None:
        evidence = (
            agent_response.retrieved_context.model_dump_json()
        )

    draft = Draft(
        ticket_id=ticket.ticket_id,
        generated_answer=agent_response.user_message,
        evidence=evidence,
        model_metadata="",
    )

    # ---------------------------------------------------------
    # 3. Persist human-review context
    # ---------------------------------------------------------

    review = Review(
        ticket_id=ticket.ticket_id,
        agent_decision=AgentDecision.ESCALATE,
        agent_reason=agent_response.support_message,
        reviewer_action=None,
        reviewer_reason=None,
    )

    db.add(draft)
    db.add(review)

    # ---------------------------------------------------------
    # 4. Atomic persistence
    # ---------------------------------------------------------

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(review)

    return review


def apply_reviewer_action(
    db: Session,
    ticket_id: int,
    action: ReviewerAction,
    reviewer_identity: str,
    edited_answer: str | None = None,
    reason: str | None = None,
):
    # ---------------------------------------------------------
    # 0. Validate reviewer identity
    # ---------------------------------------------------------

    if not reviewer_identity or not reviewer_identity.strip():
        raise ValueError("reviewer_identity is required")

    reviewer_identity = reviewer_identity.strip()

    # ---------------------------------------------------------
    # 1. Load ticket
    # ---------------------------------------------------------

    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .with_for_update()
        .first()
    )

    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} not found")

    # ---------------------------------------------------------
    # 2. Ticket must currently be waiting for human review
    # ---------------------------------------------------------

    if ticket.status != TicketStatus.REVIEW_REQUIRED:
        raise ValueError(
            f"Ticket {ticket_id} is not awaiting review"
        )

    # ---------------------------------------------------------
    # 3. Load existing review
    # ---------------------------------------------------------

    review = (
        db.query(Review)
        .filter(Review.ticket_id == ticket_id)
        .with_for_update()
        .first()
    )

    if review is None:
        raise ValueError(
            f"Review not found for ticket {ticket_id}"
        )

    # ---------------------------------------------------------
    # 4. Load draft when required
    # ---------------------------------------------------------

    draft = None

    if action in (
        ReviewerAction.RESOLVE,
        ReviewerAction.EDIT_AND_RESOLVE,
    ):
        draft = (
            db.query(Draft)
            .filter(Draft.ticket_id == ticket_id)
            .first()
        )

        if draft is None:
            raise ValueError(
                f"Draft not found for ticket {ticket_id}"
            )

    # ---------------------------------------------------------
    # 5. Apply action
    # ---------------------------------------------------------

    if action == ReviewerAction.RESOLVE:
        if not draft.generated_answer:
            raise ValueError(
                "Cannot resolve ticket without generated answer"
            )

        ticket.final_answer = draft.generated_answer
        ticket.status = TicketStatus.RESOLVED

        review.reviewer_action = ReviewerAction.RESOLVE
        review.reviewer_identity = reviewer_identity
        review.reviewer_answer = None
        review.reviewer_reason = None

        audit_event = "REVIEW_RESOLVED"

    elif action == ReviewerAction.EDIT_AND_RESOLVE:
        if not edited_answer or not edited_answer.strip():
            raise ValueError(
                "edited_answer is required for EDIT_AND_RESOLVE"
            )

        edited_answer = edited_answer.strip()

        ticket.final_answer = edited_answer
        ticket.status = TicketStatus.RESOLVED

        review.reviewer_action = ReviewerAction.EDIT_AND_RESOLVE
        review.reviewer_identity = reviewer_identity
        review.reviewer_answer = edited_answer
        review.reviewer_reason = None

        audit_event = "REVIEW_EDITED_AND_RESOLVED"

    elif action == ReviewerAction.TAKE_OVER:
        if not reason or not reason.strip():
            raise ValueError(
                "reason is required for TAKE_OVER"
            )

        reason = reason.strip()

        ticket.status = TicketStatus.ESCALATED_TO_SUPPORT

        review.reviewer_action = ReviewerAction.TAKE_OVER
        review.reviewer_identity = reviewer_identity
        review.reviewer_answer = None
        review.reviewer_reason = reason

        audit_event = "REVIEW_TAKE_OVER"

    else:
        raise ValueError(
            f"Unsupported reviewer action: {action}"
        )

    # ---------------------------------------------------------
    # 6. Persist audit event
    # ---------------------------------------------------------

    audit = Audit(
        ticket_id=ticket.ticket_id,
        event=audit_event,
        component="HUMAN_REVIEWER",
        result="SUCCESS",
    )

    db.add(audit)

    # ---------------------------------------------------------
    # 7. Atomic commit
    # ---------------------------------------------------------

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(ticket)
    db.refresh(review)

    logger.info(
        "reviewer action applied",
        extra={
            "ticket_id": ticket_id,
            "reviewer_identity": reviewer_identity,
            "reviewer_action": action.value,
            "ticket_status": ticket.status.value,
        },
    )

    return ticket, review


def get_review_queue(db: Session) -> list[ReviewItem]:
    """
    Build the reviewer read model for all tickets currently waiting
    for human review.

    This function only builds the read model.
    It does not perform reviewer actions or mutate ticket state.
    """

    rows = (
        db.query(Ticket, Review, Draft)
        .join(
            Review,
            Review.ticket_id == Ticket.ticket_id,
        )
        .outerjoin(
            Draft,
            Draft.ticket_id == Ticket.ticket_id,
        )
        .filter(
            Ticket.status == TicketStatus.REVIEW_REQUIRED,
        )
        .order_by(
            Ticket.created_at.asc(),
        )
        .all()
    )

    review_items: list[ReviewItem] = []

    for ticket, review, draft in rows:
        # -----------------------------------------------------
        # Ticket information
        # -----------------------------------------------------

        review_ticket = ReviewTicket(
            ticket_id=str(ticket.ticket_id),
            user_id=str(ticket.user_id),
            original_user_message=ticket.user_message,
            conversation=[],
            status=ticket.status,
        )

        # -----------------------------------------------------
        # Agent result
        # -----------------------------------------------------

        review_agent_result = ReviewAgentResult(
            proposed_answer=(
                draft.generated_answer
                if draft is not None
                else None
            ),
            decision=AgentAction.ESCALATE,
            reason=review.agent_reason,
        )

        # -----------------------------------------------------
        # Evidence
        # -----------------------------------------------------

        retrieved_chunks = []
        sources = []

        if draft is not None and draft.evidence:
            try:
                rag_result = RAGResult.model_validate_json(
                    draft.evidence
                )

                retrieved_chunks = rag_result.chunks

                sources = list(
                    dict.fromkeys(
                        chunk.source
                        for chunk in retrieved_chunks
                    )
                )

            except Exception as exc:
                raise ValueError(
                    f"Invalid persisted evidence for "
                    f"ticket {ticket.ticket_id}"
                ) from exc

        review_evidence = ReviewEvidence(
            retrieved_chunks=retrieved_chunks,
            sources=sources,
        )

        # -----------------------------------------------------
        # Validation
        # -----------------------------------------------------

        validation = None

        if draft is not None and draft.validation_result:
            validation = ReviewValidation(
                status=draft.validation_result,
                reason=None,
            )

        # -----------------------------------------------------
        # Complete reviewer read model
        # -----------------------------------------------------

        review_item = ReviewItem(
            ticket=review_ticket,
            agent_result=review_agent_result,
            evidence=review_evidence,
            tool_activity=[],
            validation=validation,
            escalation_context=review.agent_reason,
        )

        review_items.append(review_item)

    return review_items