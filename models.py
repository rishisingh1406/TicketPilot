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
│       ESCALATED
│
├── created_at
│   └── Required, PostgreSQL-generated timestamp
│
└── final_answer
    └── Nullable until an answer exists

"""

from enum import Enum
from json import tool
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, text ,ForeignKey
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TicketStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    ESCALATED_TO_SUPPORT = "ESCALATED_TO_SUPPORT"
    RESOLVED = "RESOLVED"
    

class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id: str = Column(
        String,
        nullable=False
    )

    user_message: str = Column(
        String,
        nullable=False
    )

    status: TicketStatus = Column(
        SQLEnum(TicketStatus),
        nullable=False,
        default=TicketStatus.CREATED
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )

    final_answer: str = Column(
        String,
        nullable=True
    )



"""

drafts

├── ticket_id
│   └── Primary key + foreign key → tickets.ticket_id
│
├── generated_answer
│   └── Nullable
│
├── evidence
│   └── Evidence / citations used to generate the answer
│
├── validation_result
│   └── Nullable, human-readable validation result
│
├── model_metadata
│   └── Information about the model/generation process
│
└── failure_reason
    └── Nullable, reason for generation failure



"""

class Draft(Base):
    __tablename__ = "drafts"

    generated_answer: str = Column(String, nullable=True)

    evidence: str = Column(String, nullable=False)

    validation_result: str = Column(String, nullable=True)

    model_metadata: str = Column(String, nullable=False)

    failure_reason: str = Column(String, nullable=True)

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.ticket_id"),
        primary_key=True
    )

"""
audit

├── audit_id
│   └── Primary key, auto-increment integer
│
├── ticket_id
│   └── Foreign key → tickets.ticket_id
│
├── event
│   └── Free-form string describing what happened
│
├── component
│   └── Free-form string identifying the component/tool
│
├── result
│   └── Free-form string describing the outcome
│
└── created_at
    └── Timestamp of when the event occurred


"""

class Audit(Base):
    __tablename__ = "audit"

    audit_id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    ticket_id: int = Column(
        Integer,
        ForeignKey("tickets.ticket_id"),
        nullable=False
    )

    event: str = Column(
        String,
        nullable=False
    )

    component: str = Column(
        String,
        nullable=False
    )

    result: str = Column(
        String,
        nullable=False
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )