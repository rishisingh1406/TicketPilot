import logging
import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session

from app.embeddings import EmbeddingModel
from app.llm import GroqLLM
from app.logging_config import configure_logging
from app.retrieval import KnowledgeRetriever
from app.ticket_service import (
    apply_reviewer_action,
    create_ticket as create_ticket_service,
    generate_ticket_draft,
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
# Application dependencies
# ============================================================

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_MODEL = os.environ["GROQ_MODEL"]

llm = GroqLLM(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
)

embedding_model = EmbeddingModel()

retriever = KnowledgeRetriever(
    embedding_model=embedding_model,
)


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
    # --------------------------------------------------------
    # Step 1: Persist ticket
    # --------------------------------------------------------

    new_ticket = create_ticket_service(
        db=db,
        user_id=ticket_data.user_id,
        message=ticket_data.message,
    )

    # --------------------------------------------------------
    # Step 2: Run bounded agent
    # --------------------------------------------------------

    result = generate_ticket_draft(
        db=db,
        ticket_id=new_ticket.ticket_id,
        llm=llm,
        retriever=retriever,
    )

    # --------------------------------------------------------
    # Step 3: Return agent result
    # --------------------------------------------------------

    agent_response = None

    if result is not None:
        if hasattr(result, "generated_answer"):
            agent_response = result.generated_answer

    return ClientResponse(
        ticket_id=str(new_ticket.ticket_id),
        status=new_ticket.status,
        message="Ticket processed successfully",
        agent_response=agent_response,
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
