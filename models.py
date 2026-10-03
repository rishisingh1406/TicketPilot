"""
tickets

├── ticket_id
│   └── Primary key, auto-increment integer
│
├── user_id
│   └── Required
│
├── user_message
│   └── Required
│
├── status
│   └── Required enum:
│       CREATED
│       PROCESSING
│       RESOLVED
│       ESCALATED_TO_SUPPORT
│
├── created_at
│   └── Required, PostgreSQL-generated timestamp
│
└── final_answer
    └── Nullable until an answer exists

"""

from enum import Enum
import hashlib

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ============================================================
# Ticket
# ============================================================


class TicketStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    ESCALATED_TO_SUPPORT = "ESCALATED_TO_SUPPORT"
    RESOLVED = "RESOLVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: str = Column(
        String,
        nullable=False,
    )

    user_message: str = Column(
        String,
        nullable=False,
    )

    status: TicketStatus = Column(
        SQLEnum(TicketStatus),
        nullable=False,
        default=TicketStatus.CREATED,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    final_answer: str = Column(
        String,
        nullable=True,
    )


# ============================================================
# Draft
# ============================================================


class Draft(Base):
    __tablename__ = "drafts"

    generated_answer: str = Column(
        String,
        nullable=True,
    )

    evidence: str = Column(
        String,
        nullable=False,
    )

    validation_result: str = Column(
        String,
        nullable=True,
    )

    model_metadata: str = Column(
        String,
        nullable=False,
    )

    failure_reason: str = Column(
        String,
        nullable=True,
    )

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.ticket_id"),
        primary_key=True,
    )


# ============================================================
# Audit
# ============================================================


class Audit(Base):
    __tablename__ = "audit"

    audit_id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    ticket_id: int = Column(
        Integer,
        ForeignKey("tickets.ticket_id"),
        nullable=False,
    )

    event: str = Column(
        String,
        nullable=False,
    )

    component: str = Column(
        String,
        nullable=False,
    )

    result: str = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


# ============================================================
# Knowledge Chunks
# ============================================================


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    chunk_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    content = Column(
        Text,
        nullable=False,
    )

    source = Column(
        String,
        nullable=False,
    )

    timestamp = Column(
        DateTime,
        nullable=True,
    )

    is_current = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    content_hash = Column(
        String,
        nullable=False,
        unique=True,
    )

    embedding = Column(
        Vector(384),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


# ============================================================
# Agent Decision
# ============================================================


class AgentDecision(str, Enum):
    ANSWER = "ANSWER"
    ESCALATE = "ESCALATE"


# ============================================================
# Reviewer Action
# ============================================================


class ReviewerAction(str, Enum):
    """
    Business outcomes available to a human reviewer.
    """

    RESOLVE = "RESOLVE"
    EDIT_AND_RESOLVE = "EDIT_AND_RESOLVE"
    TAKE_OVER = "TAKE_OVER"


# ============================================================
# Review
# ============================================================


class Review(Base):
    __tablename__ = "reviews"

    review_id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    ticket_id: int = Column(
        Integer,
        ForeignKey("tickets.ticket_id"),
        nullable=False,
    )

    # --------------------------------------------------------
    # Agent decision
    # --------------------------------------------------------

    agent_decision: AgentDecision = Column(
        SQLEnum(AgentDecision),
        nullable=False,
    )

    agent_reason: str = Column(
        String,
        nullable=False,
    )

    # --------------------------------------------------------
    # Human reviewer decision
    # --------------------------------------------------------

    reviewer_action: ReviewerAction = Column(
        SQLEnum(ReviewerAction),
        nullable=True,
    )

    reviewer_identity: str = Column(
        String,
        nullable=True,
    )

    # Final answer written/accepted by the human reviewer.
    #
    # RESOLVE:
    #     NULL because the existing AI draft is accepted.
    #
    # EDIT_AND_RESOLVE:
    #     Contains the human-edited answer.
    #
    # TAKE_OVER:
    #     NULL because support takes ownership.
    reviewer_answer: str = Column(
        String,
        nullable=True,
    )

    # Required primarily for TAKE_OVER.
    reviewer_reason: str = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
