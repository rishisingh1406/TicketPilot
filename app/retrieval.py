"""
Input:

    db session
    user query
    top_k

        ↓

EmbeddingModel

    query → vector

        ↓

pgvector

    vector → cosine distances

        ↓

PostgreSQL

    order by distance
    filter current chunks
    limit top_k

        ↓

Output:

    relevant chunks + distance
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import EmbeddingModel
from models import KnowledgeChunk


class KnowledgeRetriever:

    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model

    def retrieve_relevant_chunks(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
    ):
        # Validate query
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        # Validate top_k
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        if top_k > 20:
            raise ValueError("top_k must not exceed 20")

        # Step 1: Embed the user query into a vector
        query_embedding = self.embedding_model.embed(query)

        # Step 2: Calculate cosine distances and retrieve relevant chunks
        distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)

        statement = (
            select(KnowledgeChunk, distance)
            .where(KnowledgeChunk.is_current.is_(True))
            .order_by(distance)
            .limit(top_k)
        )

        results = db.execute(statement).all()

        # Step 3: Return the relevant chunks along with their distances
        return [(chunk, dist) for chunk, dist in results]