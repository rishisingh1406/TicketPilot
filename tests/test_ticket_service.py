from app.ticket_service import generate_ticket_draft

from models import (
    AgentDecision,
    Draft,
    Review,
    Ticket,
    TicketStatus,
)

from schemas import (
    AgentAction,
    AgentResponse,
    RAGResult,
    RetrievedChunk,
)


class FakeAgent:
    def __init__(
        self,
        system_prompt,
        user_query,
        retrieved_chunks,
        conversation_history,
        previous_tool_calls,
        previous_tool_results,
        llm,
        db,
        retriever,
        tool_handlers,
    ):
        pass

    def run(self):
        return AgentResponse(
            action=AgentAction.ANSWER,
            user_message=(
                "You can reset your password from the account settings."
            ),
        )


def test_generate_ticket_draft_creates_draft(
    db_session,
    monkeypatch,
):
    ticket = Ticket(
        user_id="123",
        user_message="I forgot my password",
    )

    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    monkeypatch.setattr(
        "app.ticket_service.Agent",
        FakeAgent,
    )

    draft = generate_ticket_draft(
        db=db_session,
        ticket_id=ticket.ticket_id,
        llm=object(),
        retriever=object(),
    )

    assert draft is not None
    assert isinstance(draft, Draft)
    assert draft.ticket_id == ticket.ticket_id

    assert (
        draft.generated_answer
        == "You can reset your password from the account settings."
    )

    # A successful agent answer must resolve the ticket.
    db_session.refresh(ticket)

    assert ticket.status == TicketStatus.RESOLVED


def test_generate_ticket_draft_persists_retrieved_evidence(
    db_session,
    monkeypatch,
):
    ticket = Ticket(
        user_id="123",
        user_message="I forgot my password",
    )

    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    class FakeAgentWithEvidence:
        def __init__(
            self,
            system_prompt,
            user_query,
            retrieved_chunks,
            conversation_history,
            previous_tool_calls,
            previous_tool_results,
            llm,
            db,
            retriever,
            tool_handlers,
        ):
            pass

        def run(self):
            return AgentResponse(
                action=AgentAction.ANSWER,
                user_message=(
                    "You can reset your password from the account settings."
                ),
                retrieved_context=RAGResult(
                    query="I forgot my password",
                    chunks=[
                        RetrievedChunk(
                            chunk_id="1",
                            content=(
                                "Users can reset their password "
                                "from account settings."
                            ),
                            source="account_access_faq",
                            timestamp=None,
                            is_current=True,
                            distance=0.22,
                        )
                    ],
                ),
            )

    monkeypatch.setattr(
        "app.ticket_service.Agent",
        FakeAgentWithEvidence,
    )

    draft = generate_ticket_draft(
        db=db_session,
        ticket_id=ticket.ticket_id,
        llm=object(),
        retriever=object(),
    )

    assert draft is not None
    assert draft.evidence
    assert "I forgot my password" in draft.evidence
    assert "Users can reset their password" in draft.evidence
    assert "account_access_faq" in draft.evidence

    stored_draft = (
        db_session.query(Draft)
        .filter(Draft.ticket_id == ticket.ticket_id)
        .first()
    )

    assert stored_draft is not None
    assert stored_draft.evidence == draft.evidence

    # Evidence-backed successful answers also resolve the ticket.
    db_session.refresh(ticket)

    assert ticket.status == TicketStatus.RESOLVED


class FakeEscalationAgent:
    def __init__(
        self,
        system_prompt,
        user_query,
        retrieved_chunks,
        conversation_history,
        previous_tool_calls,
        previous_tool_results,
        llm,
        db,
        retriever,
        tool_handlers,
    ):
        pass

    def run(self):
        return AgentResponse(
            action=AgentAction.ESCALATE,
            user_message="I need to transfer you to support.",
            support_message=(
                "The available knowledge is insufficient "
                "to answer reliably."
            ),
        )


def test_generate_ticket_draft_escalates_ticket(
    db_session,
    monkeypatch,
):
    # Arrange
    ticket = Ticket(
        user_id="user-123",
        user_message="I was charged an unexpected fee.",
    )

    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    monkeypatch.setattr(
        "app.ticket_service.Agent",
        FakeEscalationAgent,
    )

    # Act
    result = generate_ticket_draft(
        db=db_session,
        ticket_id=ticket.ticket_id,
        llm=object(),
        retriever=object(),
    )

    # Assert
    assert isinstance(result, Review)

    updated_ticket = (
        db_session.query(Ticket)
        .filter(Ticket.ticket_id == ticket.ticket_id)
        .first()
    )

    assert updated_ticket is not None

    # Agent escalation places the ticket in the human review queue.
    # It becomes ESCALATED_TO_SUPPORT only after the reviewer chooses
    # TAKE_OVER.
    assert updated_ticket.status == TicketStatus.REVIEW_REQUIRED

    review = (
        db_session.query(Review)
        .filter(Review.ticket_id == ticket.ticket_id)
        .first()
    )

    assert review is not None
    assert review.ticket_id == ticket.ticket_id
    assert review.agent_decision == AgentDecision.ESCALATE

    assert (
        review.agent_reason
        == "The available knowledge is insufficient "
        "to answer reliably."
    )

    assert review.reviewer_action is None
    assert review.reviewer_reason is None

    # Escalation also persists the agent's proposed
    # customer-facing answer as a Draft.
    stored_draft = (
        db_session.query(Draft)
        .filter(Draft.ticket_id == ticket.ticket_id)
        .first()
    )

    assert stored_draft is not None
    assert stored_draft.ticket_id == ticket.ticket_id

    assert stored_draft.generated_answer == (
        "I need to transfer you to support."
    )