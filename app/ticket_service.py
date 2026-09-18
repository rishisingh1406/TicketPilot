from sqlalchemy.orm import Session
from models import Ticket


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
