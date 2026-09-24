from app.ticket_service import generate_ticket_draft
from models import Draft, Ticket
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


def test_generate_ticket_draft_does_not_create_draft_on_escalation(
    db_session,
    monkeypatch,
):
    ticket = Ticket(
        user_id="123",
        user_message="I have a problem that requires human support",
    )

    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    class FakeEscalatingAgent:
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
                support_message="This issue requires human support.",
            )

    monkeypatch.setattr(
        "app.ticket_service.Agent",
        FakeEscalatingAgent,
    )

    draft = generate_ticket_draft(
        db=db_session,
        ticket_id=ticket.ticket_id,
        llm=object(),
        retriever=object(),
    )

    assert draft is None

    stored_draft = (
        db_session.query(Draft)
        .filter(Draft.ticket_id == ticket.ticket_id)
        .first()
    )

    assert stored_draft is None
