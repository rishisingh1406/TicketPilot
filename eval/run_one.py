import json

from app.embeddings import EmbeddingModel
from app.retrieval import KnowledgeRetriever
from database import SessionLocal

from eval.citation_judge import CitationFaithfulnessJudge
from eval.evaluator import evaluate_case
from eval.llm_factory import create_llm


with open(
    "eval/golden_set.json",
    "r",
    encoding="utf-8",
) as file:
    cases = json.load(file)


case = next(
    case
    for case in cases
    if case["id"] == "TP-024"
)


db = SessionLocal()

try:
    embedding_model = EmbeddingModel()

    retriever = KnowledgeRetriever(
        embedding_model
    )

    llm = create_llm()

    citation_judge = CitationFaithfulnessJudge(
        api_key=llm.client.api_key,
        model=llm.model,
    )

    result = evaluate_case(
        case=case,
        llm=llm,
        db=db,
        retriever=retriever,
        citation_judge=citation_judge,
    )

    print("\nEvaluation result:")
    print(
        result.model_dump_json(
            indent=2
        )
    )

finally:
    db.close()
