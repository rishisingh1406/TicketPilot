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

    finally:
        db.close()

def test_embedding_database_retrieval():
    embedding_model = EmbeddingModel()

    query = "I forgot my password. How can I reset it?"
    query_embedding = embedding_model.embed(query)

    db = SessionLocal()

    try:
        distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)

        statement = (
            select(KnowledgeChunk, distance)
            .where(KnowledgeChunk.is_current.is_(True))
            .order_by(distance)
            .limit(1)
        )

        result = db.execute(statement).first()

        assert result is not None

        chunk, similarity_distance = result

        print(f"Retrieved chunk: {chunk.content}")
        print(f"Distance: {similarity_distance}")

    finally:
        db.close()


if __name__ == "__main__":
    test_embedding_database_write()