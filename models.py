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
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TicketStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


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