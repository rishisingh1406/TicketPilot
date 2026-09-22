from app.embeddings import EmbeddingModel
from app.retrieval import KnowledgeRetriever
from database import SessionLocal


def test_retrieve_relevant_chunks(embedding_model):
    print("\nSTEP 1: Creating retriever", flush=True)
    retriever = KnowledgeRetriever(embedding_model)

    query = "I forgot my password. How can I reset it?"

    print("STEP 2: Creating database session", flush=True)
    db = SessionLocal()

    try:
        print("STEP 3: Calling retriever", flush=True)

        results = retriever.retrieve_relevant_chunks(
            db=db,
            query=query,
            top_k=3,
        )

        print("STEP 4: Retriever returned", flush=True)

        assert results

        chunk, distance = results[0]

        print(f"Retrieved chunk: {chunk.content}", flush=True)
        print(f"Distance: {distance}", flush=True)

        assert chunk.content == (
            "Users can reset their password from the account settings page."
        )

        assert distance >= 0

    finally:
        print("STEP 5: Closing database", flush=True)
        db.close()


def test_retriever_rejects_empty_query():
    embedding_model = EmbeddingModel()
    retriever = KnowledgeRetriever(embedding_model)
    db = SessionLocal()

    try:
        try:
            retriever.retrieve_relevant_chunks(
                db=db,
                query="",
                top_k=3,
            )
            assert False, "Expected ValueError for empty query"
        except ValueError as exc:
            assert str(exc) == "query must not be empty"
    finally:
        db.close()


def test_retriever_rejects_invalid_top_k():
    embedding_model = EmbeddingModel()
    retriever = KnowledgeRetriever(embedding_model)
    db = SessionLocal()

    try:
        try:
            retriever.retrieve_relevant_chunks(
                db=db,
                query="How do I reset my password?",
                top_k=0,
            )
            assert False, "Expected ValueError for top_k <= 0"
        except ValueError as exc:
            assert str(exc) == "top_k must be greater than 0"
    finally:
        db.close()


def test_retriever_rejects_excessive_top_k():
    embedding_model = EmbeddingModel()
    retriever = KnowledgeRetriever(embedding_model)
    db = SessionLocal()

    try:
        try:
            retriever.retrieve_relevant_chunks(
                db=db,
                query="How do I reset my password?",
                top_k=21,
            )
            assert False, "Expected ValueError for top_k > 20"
        except ValueError as exc:
            assert str(exc) == "top_k must not exceed 20"
    finally:
        db.close()