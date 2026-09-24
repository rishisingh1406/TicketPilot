from sqlalchemy.orm import Session

from app.agent import Agent, search_knowledge
from app.retrieval import KnowledgeRetriever
from models import Draft, Ticket
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

    return None
