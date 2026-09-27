from sqlalchemy.orm import Session

from app.agent import Agent, search_knowledge
from app.retrieval import KnowledgeRetriever
from models import Draft, Ticket , Review , AgentDecision
from schemas import (
    AgentAction,
    AgentResponse,
    AllowedTool,
    TicketStatus,
)


SYSTEM_PROMPT = """
You are TicketPilot, a SaaS support agent.

Use the available knowledge-base tools to find reliable information
before answering the customer.

Only answer when the retrieved information is sufficient to support
the answer.

If the available information is insufficient or unreliable, escalate
the ticket to human support.

Do not invent policies, account information, or facts.
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


def update_ticket_decision(
    db: Session,
    ticket_id: int,
    decision: TicketStatus,
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .first()
    )

    if ticket is None:
        return None

    ticket.status = decision

    db.commit()
    db.refresh(ticket)

    return ticket

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

    if agent_response.action == AgentAction.ANSWER:
        evidence = ""

        if agent_response.retrieved_context is not None:
            evidence = agent_response.retrieved_context.model_dump_json()

        draft = Draft(
            ticket_id=ticket.ticket_id,
            generated_answer=agent_response.user_message,
            evidence=evidence,
            model_metadata="",
        )

        db.add(draft)
        db.commit()
        db.refresh(draft)

        return draft

    if agent_response.action == AgentAction.ESCALATE:
        return escalate_ticket(
            db=db,
            ticket_id=ticket.ticket_id,
            agent_response=agent_response,
        )

    return None


def escalate_ticket(
    db: Session,
    ticket_id: int,
    agent_response: AgentResponse,
) -> Review:
    """
    Persist an agent escalation and transfer the ticket to human support.

    The ticket status update and Review creation happen in the
    same database transaction.
    """

    if agent_response.action != AgentAction.ESCALATE:
        raise ValueError("escalate_ticket requires an ESCALATE agent response")

    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .first()
    )

    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} not found")

    if not agent_response.support_message:
        raise ValueError("Escalation requires a support_message/reason")

    # Update durable ticket state
    ticket.status = TicketStatus.ESCALATED_TO_SUPPORT

    # Create human-support review/handoff record
    review = Review(
        ticket_id=ticket.ticket_id,
        agent_decision=AgentDecision.ESCALATE,
        agent_reason=agent_response.support_message,
        reviewer_action=None,
        reviewer_reason=None,
    )

    db.add(review)

    # Both changes are committed atomically
    db.commit()
    db.refresh(review)

    return review



