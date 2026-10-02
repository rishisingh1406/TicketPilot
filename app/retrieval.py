"""
Knowledge retrieval pipeline.

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

    def __init__(
        self,
        embedding_model: EmbeddingModel,
    ):
        self.embedding_model = embedding_model

    def retrieve_relevant_chunks(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
    ):
        # ========================================================
        # Validate query
        # ========================================================

        if not query or not query.strip():
            raise ValueError(
                "query must not be empty"
            )

        # ========================================================
        # Validate top_k
        # ========================================================

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0"
            )

        if top_k > 20:
            raise ValueError(
                "top_k must not exceed 20"
            )

        # ========================================================
        # Step 1: Generate query embedding
        # ========================================================

        print(
            "RETRIEVAL: generating query embedding"
        )

        query_embedding = self.embedding_model.embed(
            query
        )

        print(
            "RETRIEVAL: query embedding generated"
        )

        # ========================================================
        # Step 2: Build pgvector cosine-distance query
        # ========================================================

        distance = (
            KnowledgeChunk.embedding.cosine_distance(
                query_embedding
            )
        )

        statement = (
            select(
                KnowledgeChunk,
                distance,
            )
            .where(
                KnowledgeChunk.is_current.is_(True)
            )
            .order_by(distance)
            .limit(top_k)
        )

        # ========================================================
        # Step 3: Execute PostgreSQL query
        # ========================================================

        print(
            "RETRIEVAL: executing database query"
        )

        results = db.execute(statement).all()

        print(
            "RETRIEVAL: database query completed"
        )

        # ========================================================
        # Step 4: Return chunks + distances
        # ========================================================

        return [
            (chunk, dist)
            for chunk, dist in results
        ]
