import logging
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session

from app.logging_config import configure_logging
from app.ticket_service import (
    apply_reviewer_action,
    create_ticket as create_ticket_service,
    get_review_queue,
    get_tickets as get_tickets_service,
)
from database import get_db
from schemas import (
    ClientResponse,
    CreateTicketRequest,
    ReviewItem,
    ReviewerActionRequest,
)


# ============================================================
# Application setup
# ============================================================

configure_logging()

app = FastAPI()

logger = logging.getLogger(__name__)


# ============================================================
# Health
# ============================================================

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ============================================================
# Ticket creation
# ============================================================

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


# ============================================================
# Ticket listing
# ============================================================

@app.get("/tickets")
def get_tickets(
    db: Session = Depends(get_db),
):
    return get_tickets_service(db=db)


# ============================================================
# Request logging middleware
# ============================================================

@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
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


# ============================================================
# Human review queue
# ============================================================

@app.get(
    "/reviews",
    response_model=list[ReviewItem],
)
def get_reviews(
    db: Session = Depends(get_db),
):
    return get_review_queue(db=db)


# ============================================================
# Human review action
# ============================================================

@app.post("/reviews/{ticket_id}/action")
def reviewer_action(
    ticket_id: int,
    action_data: ReviewerActionRequest,
    db: Session = Depends(get_db),
):
    try:
        ticket, review = apply_reviewer_action(
            db=db,
            ticket_id=ticket_id,
            action=action_data.action,
            reviewer_identity=action_data.reviewer_identity,
            edited_answer=action_data.edited_answer,
            reason=action_data.reason,
        )

    except ValueError as exc:
        message = str(exc)

        if "not found" in message.lower():
            raise HTTPException(
                status_code=404,
                detail=message,
            )

        raise HTTPException(
            status_code=409,
            detail=message,
        )

    return {
        "ticket_id": ticket.ticket_id,
        "status": ticket.status,
        "reviewer_action": review.reviewer_action,
        "message": "Reviewer action applied successfully",
    }