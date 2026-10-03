import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import EmbeddingModel
from models import KnowledgeChunk


def build_content_hash(
    content: str,
    source: str,
    timestamp: datetime | None,
) -> str:
    """
    Build a deterministic identity hash for a knowledge chunk.

    The same content, source, and timestamp always produce
    the same hash.
    """
    normalized_content = content.strip()

    identity = (
        normalized_content
        + "|"
        + source
        + "|"
        + (timestamp.isoformat() if timestamp else "")
    )

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


class KnowledgeIngestion:

    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model

    def ingest_chunk(
        self,
        db: Session,
        content: str,
        source: str,
        timestamp: datetime | None = None,
        is_current: bool = True,
    ) -> KnowledgeChunk:
        """
        Generate an embedding for a knowledge chunk
        and persist it in PostgreSQL.

        Ingestion is idempotent for the same content,
        source, and timestamp.
        """

        if not content or not content.strip():
            raise ValueError("content must not be empty")

        normalized_content = content.strip()

        content_hash = build_content_hash(
            content=normalized_content,
            source=source,
            timestamp=timestamp,
        )

        # Check whether this exact knowledge version already exists.
        existing_chunk = db.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.content_hash == content_hash
            )
        ).scalar_one_or_none()

        if existing_chunk is not None:
            return existing_chunk

        embedding = self.embedding_model.embed(normalized_content)

        chunk = KnowledgeChunk(
            content=normalized_content,
            source=source,
            timestamp=timestamp,
            is_current=is_current,
            content_hash=content_hash,
            embedding=embedding,
        )

        try:
            db.add(chunk)
            db.commit()
            db.refresh(chunk)
        except Exception:
            db.rollback()
            raise

        return chunk


def chunk_document(text: str) -> list[str]:
    """
    Split a document into retrieval-friendly chunks.

    For the current TicketPilot knowledge base, each
    paragraph/FAQ section is treated as one chunk.
    """

    if not text or not text.strip():
        raise ValueError("document text must not be empty")

    chunks = [
        chunk.strip()
        for chunk in text.split("\n\n")
        if chunk.strip()
    ]

    if not chunks:
        raise ValueError("document did not contain any valid chunks")

    return chunks
