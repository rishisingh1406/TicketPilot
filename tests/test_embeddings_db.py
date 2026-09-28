from app.embeddings import EmbeddingModel
from database import SessionLocal
from models import KnowledgeChunk
from sqlalchemy import select


def test_embedding_database_write():
    embedding_model = EmbeddingModel()

    content = "Users can reset their password from the account settings page."

    embedding = embedding_model.embed(content)

    db = SessionLocal()

    try:
        chunk = KnowledgeChunk(
            content=content,
            source="test_document",
            embedding=embedding,
            is_current=True,
        )

        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        print(f"Created knowledge chunk: {chunk.chunk_id}")
        print(f"Embedding dimensions: {len(chunk.embedding)}")

        assert chunk.chunk_id is not None
        assert len(chunk.embedding) == 384
        assert chunk.content == content
        assert chunk.source == "test_document"
        assert chunk.is_current is True

    finally:
        db.close()


def test_embedding_database_retrieval():
    embedding_model = EmbeddingModel()

    content = "Users can reset their password from the account settings page."

    embedding = embedding_model.embed(content)

    db = SessionLocal()

    try:
        chunk = KnowledgeChunk(
            content=content,
            source="test_document",
            embedding=embedding,
            is_current=True,
        )

        db.add(chunk)
        db.commit()

        query = "I forgot my password. How can I reset it?"
        query_embedding = embedding_model.embed(query)

        distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)

        statement = (
            select(KnowledgeChunk, distance)
            .where(KnowledgeChunk.is_current.is_(True))
            .order_by(distance)
            .limit(1)
        )

        result = db.execute(statement).first()

        assert result is not None

        retrieved_chunk, similarity_distance = result

        print(f"Retrieved chunk: {retrieved_chunk.content}")
        print(f"Distance: {similarity_distance}")

        assert retrieved_chunk.content == content
        assert retrieved_chunk.source == "test_document"
        assert similarity_distance >= 0

    finally:
        db.rollback()
        db.query(KnowledgeChunk).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_embedding_database_write()
    test_embedding_database_retrieval()