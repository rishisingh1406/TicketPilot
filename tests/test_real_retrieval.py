from app.retrieval import KnowledgeRetriever
from database import SessionLocal


def test_password_reset_retrieval(embedding_model):
    retriever = KnowledgeRetriever(embedding_model)

    db = SessionLocal()

    try:
        results = retriever.retrieve_relevant_chunks(
            db=db,
            query="I forgot my password. How can I reset it?",
            top_k=3,
        )

        assert results

        print("\nTop 3 retrieval results:")

        for rank, (chunk, distance) in enumerate(results, start=1):
            print(f"\nResult {rank}")
            print(f"Content: {chunk.content}")
            print(f"Source: {chunk.source}")
            print(f"Current: {chunk.is_current}")
            print(f"Distance: {distance}")

        chunk, distance = results[0]

        assert chunk.is_current is True

    finally:
        db.close()



def test_outdated_knowledge_is_not_retrieved(embedding_model):
    retriever = KnowledgeRetriever(embedding_model)

    db = SessionLocal()

    try:
        results = retriever.retrieve_relevant_chunks(
            db=db,
            query="I want to cancel my AcmeCloud subscription. What is the cancellation policy?",
            top_k=5,
        )

        assert results

        print("\nCancellation retrieval results:")

        for rank, (chunk, distance) in enumerate(results, start=1):
            print(f"\nResult {rank}")
            print(f"Content: {chunk.content}")
            print(f"Source: {chunk.source}")
            print(f"Current: {chunk.is_current}")
            print(f"Distance: {distance}")

            assert chunk.is_current is True

    finally:
        db.close()
        