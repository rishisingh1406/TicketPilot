from sqlalchemy.orm import Session
from models import Ticket
from schemas import TicketStatus


def create_ticket(db: Session, user_id: int, message: str) -> Ticket:
    new_ticket = Ticket(
        user_id=str(user_id),
        user_message=message,
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket

from sqlalchemy.orm import Session
from models import Ticket


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