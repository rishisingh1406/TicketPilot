import json

from app.embeddings import EmbeddingModel
from app.retrieval import KnowledgeRetriever
from database import SessionLocal

from eval.evaluator import evaluate_case
from eval.llm_factory import create_llm


with open("eval/golden_set.json", "r", encoding="utf-8") as file:
    cases = json.load(file)

case = next(case for case in cases if case["id"] == "TP-001")

db = SessionLocal()

try:
    embedding_model = EmbeddingModel()
    retriever = KnowledgeRetriever(embedding_model)
    llm = create_llm()

    result = evaluate_case(
        case=case,
        llm=llm,
        db=db,
        retriever=retriever,
    )

    print("\nEvaluation result:")
    print(result.model_dump_json(indent=2))

finally:
    db.close()