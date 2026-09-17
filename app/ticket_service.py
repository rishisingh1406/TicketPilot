from sqlalchemy import Session

def create_ticket(db: Session, ticket_data: dict):
    from models import Ticket  # Import the Ticket model here to avoid circular imports
    new_ticket = Ticket(**ticket_data)
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket