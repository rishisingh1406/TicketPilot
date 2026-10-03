from app.retrieval import KnowledgeRetriever
from app.knowledge_ingestion import build_content_hash
from database import SessionLocal
from models import KnowledgeChunk


def test_password_reset_retrieval(embedding_model):
    retriever = KnowledgeRetriever(embedding_model)

    db = SessionLocal()

    content = (
        "Users can reset their password from the account settings page."
    )
    source = "account_access_faq"
    timestamp = None

    try:
        chunk = KnowledgeChunk(
            content=content,
            source=source,
            timestamp=timestamp,
            content_hash=build_content_hash(
                content=content,
                source=source,
                timestamp=timestamp,
            ),
            is_current=True,
            embedding=embedding_model.embed(content),
        )

        db.add(chunk)
        db.commit()

        # ... existing assertions ...

    finally:
        db.rollback()

        db.query(KnowledgeChunk).filter(
            KnowledgeChunk.content_hash
            == build_content_hash(
                content=content,
                source=source,
                timestamp=timestamp,
            )
        ).delete()

        db.commit()
        db.close()

def test_outdated_knowledge_is_not_retrieved(embedding_model):
    retriever = KnowledgeRetriever(embedding_model)

    db = SessionLocal()

    try:
        current_content = (
            "AcmeCloud subscriptions can be cancelled from the billing "
            "settings page. Cancellation takes effect at the end of the "
            "current billing period."
        )

        outdated_content = (
            "AcmeCloud subscriptions could previously be cancelled by "
            "contacting support. This cancellation policy is outdated."
        )

        current_source = "subscription_policy"
        outdated_source = "subscription_policy_old"
        timestamp = None

        current_chunk = KnowledgeChunk(
            content=current_content,
            source=current_source,
            timestamp=timestamp,
            content_hash=build_content_hash(
                content=current_content,
                source=current_source,
                timestamp=timestamp,
            ),
            is_current=True,
            embedding=embedding_model.embed(current_content),
        )

        outdated_chunk = KnowledgeChunk(
            content=outdated_content,
            source=outdated_source,
            timestamp=timestamp,
            content_hash=build_content_hash(
                content=outdated_content,
                source=outdated_source,
                timestamp=timestamp,
            ),
            is_current=False,
            embedding=embedding_model.embed(outdated_content),
        )

        db.add_all([
            current_chunk,
            outdated_chunk,
        ])
        db.commit()

        results = retriever.retrieve_relevant_chunks(
            db=db,
            query=(
                "I want to cancel my AcmeCloud subscription. "
                "What is the cancellation policy?"
            ),
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

        assert all(
            chunk.is_current is True
            for chunk, _ in results
        )

    finally:
        db.rollback()
        db.close()