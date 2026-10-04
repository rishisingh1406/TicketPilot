import json

from groq import Groq

from eval.schemas import CitationFaithfulnessResult

CITATION_FAITHFULNESS_SYSTEM_PROMPT = """
You are a citation-faithfulness evaluation judge.

Your task is to evaluate whether the GENERATED ANSWER is supported by the
RETRIEVED EVIDENCE.

Evaluate the generated answer claim-by-claim.

VERDICT RULES:

SUPPORTED:
All material factual claims in the generated answer are supported by the
retrieved evidence.

PARTIALLY_SUPPORTED:
Some material factual claims are supported, but at least one material claim
is only partially supported or lacks sufficient evidence.

UNSUPPORTED:
The retrieved evidence does not support the material claims in the generated
answer, or the evidence contradicts them.

IMPORTANT RULES:

1. Use only the retrieved evidence provided in the user message.
2. Do not use outside knowledge.
3. The expected source list is metadata only. It must NOT determine the verdict.
4. Reasonable paraphrasing is allowed.
5. If there is no retrieved evidence, factual claims cannot be considered
   supported by that evidence.
6. If the answer correctly says that the system could not verify something,
   judge the claims actually made by the answer rather than assuming missing
   evidence proves the underlying fact.
7. Return exactly one of these verdicts:
   SUPPORTED
   PARTIALLY_SUPPORTED
   UNSUPPORTED

OUTPUT REQUIREMENT:

Return ONLY valid JSON matching this exact structure:

{
  "verdict": "SUPPORTED",
  "reason": "Short explanation.",
  "unsupported_claims": []
}

The "verdict" value must be exactly one of:
SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED.

The "reason" value must be a non-empty string.

The "unsupported_claims" value must always be an array of strings.
Use [] when there are no unsupported claims.

Do not output markdown.
Do not output code fences.
Do not output any additional fields.
"""


def build_citation_faithfulness_messages(
    user_question: str,
    generated_answer: str,
    retrieved_sources: list[dict],
    expected_sources: list[str] | None = None,
) -> list[dict]:
    evidence = "\n\n".join(
        f"Source: {source['source']}\n"
        f"Content:\n{source['content']}"
        for source in retrieved_sources
    )

    expected = ", ".join(expected_sources or []) or "None provided"

    user_prompt = f"""
User question:
{user_question}

Generated answer:
{generated_answer}

Retrieved/cited evidence:
{evidence or "No evidence was provided."}

Expected source(s) from the evaluation dataset:
{expected}

Evaluate citation faithfulness according to the system rubric.
"""

    return [
        {
            "role": "system",
            "content": CITATION_FAITHFULNESS_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


class CitationFaithfulnessJudge:
    """
    LLM-based evaluator for citation faithfulness.

    This judge is intentionally separate from the production agent LLM so
    evaluation costs and token usage cannot be confused with production
    agent costs.
    """

    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

        self.call_count = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

    def reset_usage(self):
        self.call_count = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

    def evaluate(
        self,
        user_question: str,
        generated_answer: str,
        retrieved_sources: list[dict],
        expected_sources: list[str] | None = None,
    ) -> CitationFaithfulnessResult:

        messages = build_citation_faithfulness_messages(
            user_question=user_question,
            generated_answer=generated_answer,
            retrieved_sources=retrieved_sources,
            expected_sources=expected_sources,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=500,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "citation_faithfulness_result",
                    "strict": True,
                    "schema": CitationFaithfulnessResult.model_json_schema(),
                },
            },
        )

        usage = response.usage

        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.call_count += 1

        content = response.choices[0].message.content

        data = json.loads(content)

        return CitationFaithfulnessResult.model_validate(data)