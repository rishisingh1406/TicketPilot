import pytest

from app.embeddings import EmbeddingModel


@pytest.fixture(scope="session")
def embedding_model():
    return EmbeddingModel()