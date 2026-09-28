from app.ticket_service import (
    apply_reviewer_action,
    generate_ticket_draft,
)

from models import (
    AgentDecision,
    Draft,
    KnowledgeChunk,
    Review,
    Ticket,
)

from schemas import (
    AgentAction,
    AgentResponse,
    ReviewerAction,
    TicketStatus,
)


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
    from app.embeddings import EmbeddingModel
    from app.retrieval import KnowledgeRetriever

    # ---------------------------------------------------------
    # 1. Create the knowledge required by this integration test.
    # ---------------------------------------------------------
    embedding_model = EmbeddingModel()

    knowledge_text = (
        "If you forgot your password, you can reset it "
        "from your account settings."
    )

    knowledge_chunk = KnowledgeChunk(
        content=knowledge_text,
        source="account_access_faq",
        is_current=True,
        embedding=embedding_model.embed(knowledge_text),
    )

    db_session.add(knowledge_chunk)
    db_session.commit()

    # ---------------------------------------------------------
    # 2. Create the ticket.
    # ---------------------------------------------------------
    ticket = Ticket(
        user_id="123",
        user_message="I forgot my password",
    )

    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    # ---------------------------------------------------------
    # 3. Create the fake LLM and real retriever.
    # ---------------------------------------------------------
    llm = FakeLLM()
    retriever = KnowledgeRetriever(embedding_model)

    # ---------------------------------------------------------
    # 4. Run the real agent + real retrieval pipeline.
    # ---------------------------------------------------------
    draft = generate_ticket_draft(
        db=db_session,
        ticket_id=ticket.ticket_id,
        llm=llm,
        retriever=retriever,
    )

    # ---------------------------------------------------------
    # 5. Verify generated draft.
    # ---------------------------------------------------------
    assert draft is not None
    assert isinstance(draft, Draft)

    assert (
        draft.generated_answer
        == "You can reset your password from the account settings."
    )

    # ---------------------------------------------------------
    # 6. Verify retrieval evidence.
    # ---------------------------------------------------------
    assert draft.evidence
    assert "password" in draft.evidence.lower()
    assert "reset" in draft.evidence.lower()
    assert "account_access_faq" in draft.evidence

    # The agent should make exactly two LLM calls:
    # 1. TOOL_CALL
    # 2. ANSWER
    assert len(llm.calls) == 2

    # ---------------------------------------------------------
    # 7. Verify the draft was persisted.
    # ---------------------------------------------------------
    stored_draft = (
        db_session.query(Draft)
        .filter(Draft.ticket_id == ticket.ticket_id)
        .first()
    )

    assert stored_draft is not None
    assert stored_draft.evidence == draft.evidence


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


def test_agent_escalation_then_reviewer_takeover(
    db_session,
    monkeypatch,
):
    ticket = Ticket(
        user_id="integration-escalation-user",
        user_message="My account has an unexpected billing issue.",
        status=TicketStatus.CREATED,
    )

    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    monkeypatch.setattr(
        "app.ticket_service.Agent",
        FakeEscalationAgent,
    )

    # ---------------------------------------------------------
    # 1. Agent escalates the ticket.
    # ---------------------------------------------------------
    review = generate_ticket_draft(
        db=db_session,
        ticket_id=ticket.ticket_id,
        llm=object(),
        retriever=object(),
    )

    assert isinstance(review, Review)
    assert review.ticket_id == ticket.ticket_id
    assert review.agent_decision == AgentDecision.ESCALATE
    assert review.agent_reason == (
        "The available knowledge is insufficient "
        "to answer reliably."
    )
    assert review.reviewer_action is None
    assert review.reviewer_identity is None
    assert review.reviewer_reason is None

    db_session.refresh(ticket)

    # Agent escalation enters the human review queue.
    assert ticket.status == TicketStatus.REVIEW_REQUIRED

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

    # ---------------------------------------------------------
    # 2. Reviewer takes over the ticket.
    # ---------------------------------------------------------
    updated_ticket, updated_review = apply_reviewer_action(
        db=db_session,
        ticket_id=ticket.ticket_id,
        action=ReviewerAction.TAKE_OVER,
        reviewer_identity="reviewer-001",
        reason="Requires manual billing investigation.",
    )

    # ---------------------------------------------------------
    # 3. Verify final lifecycle state.
    # ---------------------------------------------------------
    assert updated_ticket.ticket_id == ticket.ticket_id

    assert (
        updated_ticket.status
        == TicketStatus.ESCALATED_TO_SUPPORT
    )

    assert updated_ticket.final_answer is None

    assert updated_review.ticket_id == ticket.ticket_id

    assert (
        updated_review.reviewer_action
        == ReviewerAction.TAKE_OVER
    )

    assert updated_review.reviewer_identity == "reviewer-001"

    assert (
        updated_review.reviewer_reason
        == "Requires manual billing investigation."
    )

    # ---------------------------------------------------------
    # 4. Verify persisted database state.
    # ---------------------------------------------------------
    db_session.refresh(ticket)
    db_session.refresh(review)

    assert (
        ticket.status
        == TicketStatus.ESCALATED_TO_SUPPORT
    )

    assert (
        review.reviewer_action
        == ReviewerAction.TAKE_OVER
    )

    assert review.reviewer_identity == "reviewer-001"

    assert (
        review.reviewer_reason
        == "Requires manual billing investigation."
    )