import pytest

from app.embeddings import EmbeddingModel
from database import SessionLocal
from models import Audit, Draft, KnowledgeChunk, Review, Ticket


@pytest.fixture(scope="session")
def embedding_model():
    return EmbeddingModel()


@pytest.fixture
def db_session():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.rollback()

        db.query(Audit).delete()
        db.query(Draft).delete()
        db.query(Review).delete()
        db.query(KnowledgeChunk).delete()
        db.query(Ticket).delete()

        db.commit()
        db.close()