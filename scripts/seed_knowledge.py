import json
from datetime import datetime
from pathlib import Path

from app.embeddings import EmbeddingModel
from app.knowledge_ingestion import KnowledgeIngestion
from database import SessionLocal


def main():
    knowledge_file = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "knowledge_base.json"
    )

    print("Loading knowledge base...", flush=True)

    with knowledge_file.open("r", encoding="utf-8") as file:
        knowledge_chunks = json.load(file)

    print(
        f"Loaded {len(knowledge_chunks)} knowledge chunks",
        flush=True,
    )

    embedding_model = EmbeddingModel()
    ingestion = KnowledgeIngestion(embedding_model)

    db = SessionLocal()

    try:
        for index, chunk_data in enumerate(knowledge_chunks, start=1):
            timestamp = chunk_data.get("timestamp")

            if timestamp:
                timestamp = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )

            ingestion.ingest_chunk(
                db=db,
                content=chunk_data["content"],
                source=chunk_data["source"],
                timestamp=timestamp,
                is_current=chunk_data.get("is_current", True),
            )

            print(
                f"Ingested {index}/{len(knowledge_chunks)}",
                flush=True,
            )

    except Exception as exc:
        print(
            f"Seed failed: {type(exc).__name__}: {exc}",
            flush=True,
        )
        raise

    finally:
        db.close()

    print("Knowledge base ingestion complete.", flush=True)


if __name__ == "__main__":
    main()