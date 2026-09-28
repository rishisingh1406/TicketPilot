from fastapi.testclient import TestClient

from app.main import app
from database import SessionLocal
from models import (
    AgentDecision,
    Draft,
    Review,
    Ticket,
    TicketStatus,
)


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_ticket():
    response = client.post(
        "/tickets",
        json={
            "user_id": 123,
            "message": "I was charged extra",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticket_id"]
    assert data["status"] == "CREATED"
    assert data["message"] == "Ticket created successfully"


def test_create_ticket_rejects_empty_message():
    response = client.post(
        "/tickets",
        json={
            "user_id": 123,
            "message": "",
        },
    )

    assert response.status_code == 422


def test_get_tickets():
    response = client.get("/tickets")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


def test_get_reviews_returns_empty_list_when_queue_is_empty():
    response = client.get("/reviews")

    assert response.status_code == 200
    assert response.json() == []


def test_get_reviews_returns_review_required_ticket():
    db = SessionLocal()

    try:
        ticket = Ticket(
            user_id="user-123",
            user_message="I was charged twice",
            status=TicketStatus.REVIEW_REQUIRED,
        )

        db.add(ticket)
        db.flush()

        draft = Draft(
            ticket_id=ticket.ticket_id,
            generated_answer="We need to investigate the duplicate charge.",
            evidence="",
            validation_result=None,
            model_metadata="test-model",
        )

        review = Review(
            ticket_id=ticket.ticket_id,
            agent_decision=AgentDecision.ESCALATE,
            agent_reason="The account requires human review.",
        )

        db.add(draft)
        db.add(review)
        db.commit()

        response = client.get("/reviews")

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1

        review_item = data[0]

        assert review_item["ticket"]["ticket_id"] == str(ticket.ticket_id)
        assert review_item["ticket"]["user_id"] == "user-123"
        assert review_item["ticket"]["status"] == "REVIEW_REQUIRED"

        assert (
            review_item["agent_result"]["proposed_answer"]
            == "We need to investigate the duplicate charge."
        )
        assert review_item["agent_result"]["decision"] == "ESCALATE"
        assert (
            review_item["agent_result"]["reason"]
            == "The account requires human review."
        )

        assert (
            review_item["escalation_context"]
            == "The account requires human review."
        )

    finally:
        db.rollback()
        db.close()


def test_get_reviews_excludes_resolved_ticket():
    db = SessionLocal()

    try:
        ticket = Ticket(
            user_id="user-456",
            user_message="My password is not working",
            status=TicketStatus.RESOLVED,
        )

        db.add(ticket)
        db.commit()

        response = client.get("/reviews")

        assert response.status_code == 200

        data = response.json()

        assert all(
            item["ticket"]["ticket_id"] != str(ticket.ticket_id)
            for item in data
        )

    finally:
        db.rollback()
        db.close()


def test_reviewer_action_resolve():
    db = SessionLocal()

    try:
        ticket = Ticket(
            user_id="user-789",
            user_message="I was charged twice",
            status=TicketStatus.REVIEW_REQUIRED,
        )

        db.add(ticket)
        db.flush()

        draft = Draft(
            ticket_id=ticket.ticket_id,
            generated_answer="We will investigate the duplicate charge.",
            evidence="",
            validation_result=None,
            model_metadata="test-model",
        )

        review = Review(
            ticket_id=ticket.ticket_id,
            agent_decision=AgentDecision.ESCALATE,
            agent_reason="Requires human review.",
        )

        db.add(draft)
        db.add(review)
        db.commit()

        response = client.post(
            f"/reviews/{ticket.ticket_id}/action",
            json={
                "action": "RESOLVE",
                "reviewer_identity": "reviewer-1",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["ticket_id"] == ticket.ticket_id
        assert data["status"] == "RESOLVED"
        assert data["reviewer_action"] == "RESOLVE"

    finally:
        db.rollback()
        db.close()


def test_reviewer_action_edit_and_resolve():
    db = SessionLocal()

    try:
        ticket = Ticket(
            user_id="user-edit",
            user_message="I was charged twice",
            status=TicketStatus.REVIEW_REQUIRED,
        )

        db.add(ticket)
        db.flush()

        draft = Draft(
            ticket_id=ticket.ticket_id,
            generated_answer="We will investigate the duplicate charge.",
            evidence="",
            validation_result=None,
            model_metadata="test-model",
        )

        review = Review(
            ticket_id=ticket.ticket_id,
            agent_decision=AgentDecision.ESCALATE,
            agent_reason="Requires human review.",
        )

        db.add(draft)
        db.add(review)
        db.commit()

        response = client.post(
            f"/reviews/{ticket.ticket_id}/action",
            json={
                "action": "EDIT_AND_RESOLVE",
                "reviewer_identity": "reviewer-2",
                "edited_answer": "We have reviewed your account and will refund the duplicate charge.",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["ticket_id"] == ticket.ticket_id
        assert data["status"] == "RESOLVED"
        assert data["reviewer_action"] == "EDIT_AND_RESOLVE"

    finally:
        db.rollback()
        db.close()


def test_reviewer_action_take_over():
    db = SessionLocal()

    try:
        ticket = Ticket(
            user_id="user-takeover",
            user_message="I need help with my account",
            status=TicketStatus.REVIEW_REQUIRED,
        )

        db.add(ticket)
        db.flush()

        draft = Draft(
            ticket_id=ticket.ticket_id,
            generated_answer="A support representative should review this request.",
            evidence="",
            validation_result=None,
            model_metadata="test-model",
        )

        review = Review(
            ticket_id=ticket.ticket_id,
            agent_decision=AgentDecision.ESCALATE,
            agent_reason="The request requires manual support.",
        )

        db.add(draft)
        db.add(review)
        db.commit()

        response = client.post(
            f"/reviews/{ticket.ticket_id}/action",
            json={
                "action": "TAKE_OVER",
                "reviewer_identity": "reviewer-3",
                "reason": "Customer requires direct support assistance.",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["ticket_id"] == ticket.ticket_id
        assert data["status"] == "ESCALATED_TO_SUPPORT"
        assert data["reviewer_action"] == "TAKE_OVER"

    finally:
        db.rollback()
        db.close()