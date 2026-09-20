from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import CreateTicketRequest, ClientResponse
from app.ticket_service import create_ticket as create_ticket_service

from app.ticket_service import (
    create_ticket as create_ticket_service,
    get_tickets as get_tickets_service,
    update_ticket_decision,
)

from schemas import (
    CreateTicketRequest,
    ClientResponse,
    TicketDecisionRequest,
)

from fastapi import FastAPI, Depends, HTTPException
from app.logging_config import configure_logging

import logging
import uuid

from fastapi import Request

configure_logging()

app = FastAPI()

logger = logging.getLogger(__name__)


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


@app.post("/tickets/{ticket_id}/decision")
def make_ticket_decision(
    ticket_id: int,
    decision_data: TicketDecisionRequest,
    db: Session = Depends(get_db),
):
    ticket = update_ticket_decision(
        db=db,
        ticket_id=ticket_id,
        decision=decision_data.decision,
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return ClientResponse(
        ticket_id=str(ticket.ticket_id),
        status=ticket.status,
        message="Ticket decision updated successfully",
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        },
    )

    response.headers["X-Request-ID"] = request_id

    return response