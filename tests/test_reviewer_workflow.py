import pytest

from app.ticket_service import apply_reviewer_action
from models import (
    AgentDecision,
    Audit,
    Draft,
    Review,
    Ticket,
    TicketStatus,
)
from schemas import ReviewerAction


def test_reviewer_resolve(db_session):
    ticket = Ticket(
        user_id="123",
        user_message="How do I reset my password?",
        status=TicketStatus.REVIEW_REQUIRED,
    )

    db_session.add(ticket)
    db_session.flush()

    draft = Draft(
        ticket_id=ticket.ticket_id,
        generated_answer="You can reset your password from Account Settings.",
        evidence="account_access_faq",
        model_metadata="test",
    )

    review = Review(
        ticket_id=ticket.ticket_id,
        agent_decision=AgentDecision.ESCALATE,
        agent_reason="Requires human review",
    )

    db_session.add_all([draft, review])
    db_session.commit()

    ticket, review = apply_reviewer_action(
        db=db_session,
        ticket_id=ticket.ticket_id,
        action=ReviewerAction.RESOLVE,
        reviewer_identity="reviewer-1",
    )

    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.final_answer == draft.generated_answer

    assert review.reviewer_action == ReviewerAction.RESOLVE
    assert review.reviewer_identity == "reviewer-1"
    assert review.reviewer_answer is None
    assert review.reviewer_reason is None

    audit = (
        db_session.query(Audit)
        .filter(Audit.ticket_id == ticket.ticket_id)
        .one()
    )

    assert audit.event == "REVIEW_RESOLVED"
    assert audit.component == "HUMAN_REVIEWER"
    assert audit.result == "SUCCESS"


def test_reviewer_edit_and_resolve(db_session):
    ticket = Ticket(
        user_id="123",
        user_message="How do I reset my password?",
        status=TicketStatus.REVIEW_REQUIRED,
    )

    db_session.add(ticket)
    db_session.flush()

    original_answer = "Reset your password from Account Settings."

    draft = Draft(
        ticket_id=ticket.ticket_id,
        generated_answer=original_answer,
        evidence="account_access_faq",
        model_metadata="test",
    )

    review = Review(
        ticket_id=ticket.ticket_id,
        agent_decision=AgentDecision.ESCALATE,
        agent_reason="Requires human review",
    )

    db_session.add_all([draft, review])
    db_session.commit()

    edited_answer = "Go to Account Settings → Security → Reset Password."

    ticket, review = apply_reviewer_action(
        db=db_session,
        ticket_id=ticket.ticket_id,
        action=ReviewerAction.EDIT_AND_RESOLVE,
        reviewer_identity="reviewer-1",
        edited_answer=edited_answer,
    )

    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.final_answer == edited_answer

    # Original AI answer must remain unchanged.
    assert draft.generated_answer == original_answer

    assert review.reviewer_action == ReviewerAction.EDIT_AND_RESOLVE
    assert review.reviewer_identity == "reviewer-1"
    assert review.reviewer_answer == edited_answer
    assert review.reviewer_reason is None

    audit = (
        db_session.query(Audit)
        .filter(Audit.ticket_id == ticket.ticket_id)
        .one()
    )

    assert audit.event == "REVIEW_EDITED_AND_RESOLVED"
    assert audit.component == "HUMAN_REVIEWER"
    assert audit.result == "SUCCESS"


def test_reviewer_take_over(db_session):
    ticket = Ticket(
        user_id="123",
        user_message="I need help with an unusual billing issue.",
        status=TicketStatus.REVIEW_REQUIRED,
    )

    db_session.add(ticket)
    db_session.flush()

    review = Review(
        ticket_id=ticket.ticket_id,
        agent_decision=AgentDecision.ESCALATE,
        agent_reason="Insufficient evidence",
    )

    db_session.add(review)
    db_session.commit()

    reason = "Customer requires manual billing investigation."

    ticket, review = apply_reviewer_action(
        db=db_session,
        ticket_id=ticket.ticket_id,
        action=ReviewerAction.TAKE_OVER,
        reviewer_identity="reviewer-1",
        reason=reason,
    )

    assert ticket.status == TicketStatus.ESCALATED_TO_SUPPORT
    assert ticket.final_answer is None

    assert review.reviewer_action == ReviewerAction.TAKE_OVER
    assert review.reviewer_identity == "reviewer-1"
    assert review.reviewer_answer is None
    assert review.reviewer_reason == reason

    audit = (
        db_session.query(Audit)
        .filter(Audit.ticket_id == ticket.ticket_id)
        .one()
    )

    assert audit.event == "REVIEW_TAKE_OVER"
    assert audit.component == "HUMAN_REVIEWER"
    assert audit.result == "SUCCESS"


def test_reviewer_cannot_act_on_resolved_ticket(db_session):
    ticket = Ticket(
        user_id="123",
        user_message="Already resolved ticket",
        status=TicketStatus.RESOLVED,
        final_answer="Already resolved.",
    )

    db_session.add(ticket)
    db_session.commit()

    with pytest.raises(ValueError, match="not awaiting review"):
        apply_reviewer_action(
            db=db_session,
            ticket_id=ticket.ticket_id,
            action=ReviewerAction.RESOLVE,
            reviewer_identity="reviewer-1",
        )


def test_reviewer_resolve_requires_draft(db_session):
    ticket = Ticket(
        user_id="123",
        user_message="How do I reset my password?",
        status=TicketStatus.REVIEW_REQUIRED,
    )

    db_session.add(ticket)
    db_session.flush()

    review = Review(
        ticket_id=ticket.ticket_id,
        agent_decision=AgentDecision.ESCALATE,
        agent_reason="Requires human review",
    )

    db_session.add(review)
    db_session.commit()

    with pytest.raises(ValueError, match="Draft not found"):
        apply_reviewer_action(
            db=db_session,
            ticket_id=ticket.ticket_id,
            action=ReviewerAction.RESOLVE,
            reviewer_identity="reviewer-1",
        )


def test_reviewer_edit_and_resolve_requires_answer(db_session):
    ticket = Ticket(
        user_id="123",
        user_message="How do I reset my password?",
        status=TicketStatus.REVIEW_REQUIRED,
    )

    db_session.add(ticket)
    db_session.flush()

    draft = Draft(
        ticket_id=ticket.ticket_id,
        generated_answer="Original AI answer.",
        evidence="account_access_faq",
        model_metadata="test",
    )

    review = Review(
        ticket_id=ticket.ticket_id,
        agent_decision=AgentDecision.ESCALATE,
        agent_reason="Requires human review",
    )

    db_session.add_all([draft, review])
    db_session.commit()

    with pytest.raises(ValueError, match="edited_answer is required"):
        apply_reviewer_action(
            db=db_session,
            ticket_id=ticket.ticket_id,
            action=ReviewerAction.EDIT_AND_RESOLVE,
            reviewer_identity="reviewer-1",
            edited_answer="   ",
        )


def test_reviewer_take_over_requires_reason(db_session):
    ticket = Ticket(
        user_id="123",
        user_message="Unusual billing issue",
        status=TicketStatus.REVIEW_REQUIRED,
    )

    db_session.add(ticket)
    db_session.flush()

    review = Review(
        ticket_id=ticket.ticket_id,
        agent_decision=AgentDecision.ESCALATE,
        agent_reason="Insufficient evidence",
    )

    db_session.add(review)
    db_session.commit()

    with pytest.raises(ValueError, match="reason is required"):
        apply_reviewer_action(
            db=db_session,
            ticket_id=ticket.ticket_id,
            action=ReviewerAction.TAKE_OVER,
            reviewer_identity="reviewer-1",
            reason="   ",
        )