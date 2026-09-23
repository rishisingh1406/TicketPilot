from sqlalchemy.orm import Session

from app.agent import Agent
from app.retrieval import KnowledgeRetriever
from models import Draft, Ticket
from schemas import AgentAction, AgentResponse, TicketStatus


def create_ticket(db: Session, user_id: int, message: str) -> Ticket:
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
        user_message=ticket.user_message,
        llm=llm,
        db=db,
        retriever=retriever,
    )

    agent_response: AgentResponse = agent.run()

    if agent_response.action == AgentAction.ANSWER:
        draft = Draft(
            ticket_id=ticket.ticket_id,
            generated_answer=agent_response.user_message,
            evidence="",
            model_metadata="",
        )

        db.add(draft)
        db.commit()
        db.refresh(draft)

        return draft

    return None