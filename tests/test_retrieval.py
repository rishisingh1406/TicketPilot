from app.retrieval import KnowledgeRetriever
from app.knowledge_ingestion import build_content_hash
from database import SessionLocal
from models import KnowledgeChunk


def test_retrieve_relevant_chunks(embedding_model):
    print("\nSTEP 1: Creating retriever", flush=True)
    retriever = KnowledgeRetriever(embedding_model)

    content = "Users can reset their password from the account settings page."
    source = "account_access_faq"
    timestamp = None

    embedding = embedding_model.embed(content)

    content_hash = build_content_hash(
        content=content,
        source=source,
        timestamp=timestamp,
    )

    print("STEP 2: Creating database session", flush=True)
    db = SessionLocal()

    try:
        chunk = KnowledgeChunk(
            content=content,
            source=source,
            timestamp=timestamp,
            content_hash=content_hash,
            embedding=embedding,
            is_current=True,
        )

        db.add(chunk)
        db.commit()

        print("STEP 3: Calling retriever", flush=True)

        results = retriever.retrieve_relevant_chunks(
            db=db,
            query="I forgot my password. How can I reset it?",
            top_k=3,
        )

        print("STEP 4: Retriever returned", flush=True)

        assert results

        chunk, distance = results[0]

        print(f"Retrieved chunk: {chunk.content}", flush=True)
        print(f"Distance: {distance}", flush=True)

        assert chunk.content == content
        assert chunk.source == source
        assert chunk.is_current is True
        assert chunk.content_hash == content_hash
        assert distance >= 0

    finally:
        db.rollback()
        db.query(KnowledgeChunk).delete()
        db.commit()
        db.close()


def test_retriever_rejects_empty_query():
    retriever = KnowledgeRetriever(embedding_model=None)
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
    retriever = KnowledgeRetriever(embedding_model=None)
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
    retriever = KnowledgeRetriever(embedding_model=None)
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