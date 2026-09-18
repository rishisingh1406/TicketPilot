from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import CreateTicketRequest, ClientResponse
from app.ticket_service import create_ticket as create_ticket_service

from app.ticket_service import (
    create_ticket as create_ticket_service,
    get_tickets as get_tickets_service,
)

app = FastAPI()



@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/tickets", response_model=ClientResponse)
def create_ticket(
    ticket_data: CreateTicketRequest,
    db: Session = Depends(get_db),
):
    new_ticket = create_ticket_service(
        db=db,
        user_id=ticket_data.user_id,
        message=ticket_data.message,
    )

    return ClientResponse(
        ticket_id=str(new_ticket.ticket_id),
        status=new_ticket.status,
        message="Ticket created successfully",
    )










@app.get("/tickets")
def get_tickets(db: Session = Depends(get_db)):
    tickets = get_tickets_service(db=db)
    return tickets
