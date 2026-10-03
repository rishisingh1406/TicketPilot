from app.embeddings import EmbeddingModel
from app.knowledge_ingestion import build_content_hash
from database import SessionLocal
from models import KnowledgeChunk
from sqlalchemy import select


def test_embedding_database_write():
    embedding_model = EmbeddingModel()

    content = "Users can reset their password from the account settings page."
    source = "test_document"
    timestamp = None

    embedding = embedding_model.embed(content)

    db = SessionLocal()

    try:
        chunk = KnowledgeChunk(
            content=content,
            source=source,
            timestamp=timestamp,
            embedding=embedding,
            is_current=True,
            content_hash=build_content_hash(
                content=content,
                source=source,
                timestamp=timestamp,
            ),
        )

        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        print(f"Created knowledge chunk: {chunk.chunk_id}")
        print(f"Embedding dimensions: {len(chunk.embedding)}")

        assert chunk.chunk_id is not None
        assert len(chunk.embedding) == 384
        assert chunk.content == content
        assert chunk.source == source
        assert chunk.is_current is True
        assert chunk.content_hash is not None

    finally:
        db.rollback()

        # Remove only the test data created by this test.
        db.query(KnowledgeChunk).filter(
            KnowledgeChunk.source == source
        ).delete()

        db.commit()
        db.close()


def test_embedding_database_retrieval():
    embedding_model = EmbeddingModel()

    content = "Users can reset their password from the account settings page."
    source = "test_document"
    timestamp = None

    embedding = embedding_model.embed(content)

    db = SessionLocal()

    try:
        chunk = KnowledgeChunk(
            content=content,
            source=source,
            timestamp=timestamp,
            embedding=embedding,
            is_current=True,
            content_hash=build_content_hash(
                content=content,
                source=source,
                timestamp=timestamp,
            ),
        )

        db.add(chunk)
        db.commit()

        query = "I forgot my password. How can I reset it?"
        query_embedding = embedding_model.embed(query)

        distance = KnowledgeChunk.embedding.cosine_distance(
            query_embedding
        )

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
        assert retrieved_chunk.source == source
        assert similarity_distance >= 0

    finally:
        db.rollback()

        # Remove only the test data created by this test.
        db.query(KnowledgeChunk).filter(
            KnowledgeChunk.source == source
        ).delete()

        db.commit()
        db.close()


if __name__ == "__main__":
    test_embedding_database_write()
    test_embedding_database_retrieval()