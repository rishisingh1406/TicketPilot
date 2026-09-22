from datetime import datetime

from sqlalchemy.orm import Session

from app.embeddings import EmbeddingModel
from models import KnowledgeChunk


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
        """

        if not content or not content.strip():
            raise ValueError("content must not be empty")

        embedding = self.embedding_model.embed(content)

        chunk = KnowledgeChunk(
            content=content.strip(),
            source=source,
            timestamp=timestamp,
            is_current=is_current,
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

