from app.ticket_service import generate_ticket_draft
from models import Draft, Ticket
from schemas import AgentAction, AgentResponse


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)

        # First LLM call: ask the agent to search the knowledge base.
        if len(self.calls) == 1:
            return AgentResponse(
                action=AgentAction.TOOL_CALL,
                tool="SEARCH_KNOWLEDGE",
                tool_input={
                    "query": "password reset",
                },
            )

        # Second LLM call: the real Agent has now received
        # the real retrieval result.
        return AgentResponse(
            action=AgentAction.ANSWER,
            user_message=(
                "You can reset your password from the account settings."
            ),
        )


def test_generate_ticket_draft_with_real_agent_and_retrieval(
    db_session,
):
    ticket = Ticket(
        user_id="123",
        user_message="I forgot my password",
    )

    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    llm = FakeLLM()

    from app.embeddings import EmbeddingModel
    from app.retrieval import KnowledgeRetriever

    embedding_model = EmbeddingModel()
    retriever = KnowledgeRetriever(embedding_model)

    draft = generate_ticket_draft(
        db=db_session,
        ticket_id=ticket.ticket_id,
        llm=llm,
        retriever=retriever,
    )

    assert draft is not None
    assert isinstance(draft, Draft)

    assert (
        draft.generated_answer
        == "You can reset your password from the account settings."
    )

    assert draft.evidence

    assert "password" in draft.evidence.lower()
    assert "reset" in draft.evidence.lower()
    assert "account_access_faq" in draft.evidence

    assert len(llm.calls) == 2

    stored_draft = (
        db_session.query(Draft)
        .filter(Draft.ticket_id == ticket.ticket_id)
        .first()
    )

    assert stored_draft is not None
    assert stored_draft.evidence == draft.evidence