import pytest

from app.embeddings import EmbeddingModel
from database import SessionLocal


@pytest.fixture(scope="session")
def embedding_model():
    return EmbeddingModel()


@pytest.fixture
def db_session():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()