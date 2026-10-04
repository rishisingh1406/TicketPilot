import json

from app.embeddings import EmbeddingModel
from app.retrieval import KnowledgeRetriever
from database import SessionLocal

from eval.citation_judge import CitationFaithfulnessJudge
from eval.evaluator import evaluate_case
from eval.llm_factory import create_llm


def main():
    with open("eval/golden_set.json", "r", encoding="utf-8") as file:
        cases = json.load(file)

    print(f"Loaded {len(cases)} evaluation cases")

    embedding_model = EmbeddingModel()
    retriever = KnowledgeRetriever(embedding_model)
    llm = create_llm()

    citation_judge = CitationFaithfulnessJudge(
        api_key=llm.client.api_key,
        model=llm.model,
    )

    results = []

    db = SessionLocal()

    try:
        for index, case in enumerate(cases, start=1):
            print(
                f"\n[{index}/{len(cases)}] "
                f"Evaluating {case['id']}..."
            )

            result = evaluate_case(
                case=case,
                llm=llm,
                db=db,
                retriever=retriever,
                citation_judge=citation_judge,
            )

            results.append(result)

            print(
                f"  expected={result.expected_action} "
                f"actual={result.actual_action} "
                f"valid={result.structured_output_valid} "
                f"latency={result.latency_ms:.0f}ms "
                f"error={result.production_error}"
            )

    finally:
        db.close()

    total = len(results)

    action_correct = sum(
        1
        for result in results
        if result.actual_action == result.expected_action
    )

    structured_valid = sum(
        1
        for result in results
        if result.structured_output_valid
    )

    citation_cases = [
        result
        for result in results
        if result.citation_correct is not None
    ]

    citation_correct = sum(
        1
        for result in citation_cases
        if result.citation_correct
    )

    faithfulness_cases = [
        result
        for result in results
        if result.citation_faithfulness is not None
    ]

    faithfulness_supported = sum(
        1
        for result in faithfulness_cases
        if result.citation_faithfulness.value == "SUPPORTED"
    )

    faithfulness_partial = sum(
        1
        for result in faithfulness_cases
        if result.citation_faithfulness.value == "PARTIALLY_SUPPORTED"
    )

    faithfulness_unsupported = sum(
        1
        for result in faithfulness_cases
        if result.citation_faithfulness.value == "UNSUPPORTED"
    )

    expected_escalations = sum(
        1
        for result in results
        if result.expected_action.value == "ESCALATE"
    )

    actual_escalations = sum(
        1
        for result in results
        if (
            result.actual_action is not None
            and result.actual_action.value == "ESCALATE"
        )
    )

    true_positive_escalations = sum(
        1
        for result in results
        if (
            result.expected_action.value == "ESCALATE"
            and result.actual_action is not None
            and result.actual_action.value == "ESCALATE"
        )
    )

    escalation_precision = (
        true_positive_escalations / actual_escalations
        if actual_escalations
        else None
    )

    escalation_recall = (
        true_positive_escalations / expected_escalations
        if expected_escalations
        else None
    )

    latencies = [
        result.latency_ms
        for result in results
    ]

    average_latency = (
        sum(latencies) / len(latencies)
        if latencies
        else 0
    )

    p95_latency = sorted(latencies)[
        min(
            len(latencies) - 1,
            int(len(latencies) * 0.95),
        )
    ]

    errors = [
        result
        for result in results
        if result.production_error is not None
    ]

    total_production_cost = sum(
        result.cost_usd
        for result in results
    )

    total_judge_cost = sum(
        result.judge_cost_usd
        for result in results
    )

    total_cost = (
        total_production_cost
        + total_judge_cost
    )

    print("\n" + "=" * 60)
    print("TICKETPILOT EVALUATION BASELINE")
    print("=" * 60)

    print(f"Total cases:              {total}")

    print(
        f"Action accuracy:          "
        f"{action_correct / total:.2%}"
    )

    print(
        f"Structured output valid:  "
        f"{structured_valid / total:.2%}"
    )

    if citation_cases:
        print(
            f"Citation correctness:     "
            f"{citation_correct / len(citation_cases):.2%}"
        )
    else:
        print("Citation correctness:     N/A")

    if faithfulness_cases:
        print(
            f"Citation faithfulness:    "
            f"{faithfulness_supported / len(faithfulness_cases):.2%} "
            f"SUPPORTED"
        )

        print(
            f"  Partially supported:    "
            f"{faithfulness_partial}"
        )

        print(
            f"  Unsupported:            "
            f"{faithfulness_unsupported}"
        )
    else:
        print("Citation faithfulness:    N/A")

    print(
        f"Escalation precision:     "
        f"{escalation_precision:.2%}"
        if escalation_precision is not None
        else "Escalation precision:     N/A"
    )

    print(
        f"Escalation recall:        "
        f"{escalation_recall:.2%}"
        if escalation_recall is not None
        else "Escalation recall:        N/A"
    )

    print(
        f"Average latency:          "
        f"{average_latency:.0f} ms"
    )

    print(
        f"P95 latency:              "
        f"{p95_latency:.0f} ms"
    )

    print(
        f"Production cost:          "
        f"${total_production_cost:.4f}"
    )

    print(
        f"Judge cost:               "
        f"${total_judge_cost:.4f}"
    )

    print(
        f"Total evaluation cost:    "
        f"${total_cost:.4f}"
    )

    print(f"Errors:                   {len(errors)}")

    if errors:
        print("\nFailed cases:")

        for result in errors:
            print(
                f"- {result.case_id}: "
                f"{result.production_error}"
            )

    print("=" * 60)

    with open(
        "eval/baseline_results.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            [
                result.model_dump(mode="json")
                for result in results
            ],
            file,
            indent=2,
        )

    print(
        "\nDetailed results saved to "
        "eval/baseline_results.json"
    )


if __name__ == "__main__":
    main()
