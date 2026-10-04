from eval.citation_judge import (
    CitationFaithfulnessJudge,
    build_citation_faithfulness_messages,
)
from eval.schemas import CitationFaithfulnessVerdict


CITATION_FAITHFULNESS_SYSTEM_PROMPT = """
You are an evaluation judge for an AI support-ticket system.

Your task is to determine whether a generated answer is supported by the
retrieved evidence provided to you.

Evaluate the answer claim-by-claim.

Verdicts:

SUPPORTED:
Every material factual claim in the answer is supported by the supplied evidence.

PARTIALLY_SUPPORTED:
Some material factual claims are supported, but at least one material claim
is unsupported or only partially supported.

UNSUPPORTED:
The answer contains material factual claims that are not supported by the
supplied evidence.

Rules:

1. Judge only against the supplied evidence.
2. Do not use outside knowledge.
3. Do not judge whether the cited source is the best possible source.
4. A valid paraphrase of the evidence is supported.
5. Matching the source name is not sufficient.
6. The actual evidence must support the claim.
7. If the answer contains unsupported factual details, identify them.
8. Keep the reason concise and evidence-based.
9. Return only the requested structured output.
"""


def build_citation_faithfulness_messages(
    user_question: str,
    generated_answer: str,
    retrieved_sources: list[dict],
    expected_sources: list[str] | None = None,
) -> list[dict]:

    evidence_blocks = []

    for source in retrieved_sources:
        evidence_blocks.append(
            f"""
SOURCE: {source["source"]}

CONTENT:
{source["content"]}
"""
        )

    evidence = "\n".join(evidence_blocks)

    expected = expected_sources or []

    user_prompt = f"""
USER QUESTION:
{user_question}

GENERATED ANSWER:
{generated_answer}

RETRIEVED EVIDENCE:
{evidence}

EXPECTED SOURCES:
{expected}

Determine whether the generated answer is supported by the retrieved evidence.

The expected source list is contextual information only and must not determine
the faithfulness verdict.
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


from eval.citation_judge import (
    build_citation_faithfulness_messages,
)


def test_build_citation_faithfulness_messages_returns_system_and_user_messages():
    messages = build_citation_faithfulness_messages(
        user_question="What is the API rate limit?",
        generated_answer="The standard plan allows 1,000 requests per minute.",
        retrieved_sources=[
            {
                "source": "api_usage_policy",
                "content": "The standard plan allows 1,000 requests per minute.",
            }
        ],
        expected_sources=["api_usage_policy"],
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_prompt_contains_question_and_generated_answer():
    messages = build_citation_faithfulness_messages(
        user_question="What is the API rate limit?",
        generated_answer="The standard plan allows 1,000 requests per minute.",
        retrieved_sources=[],
    )

    user_prompt = messages[1]["content"]

    assert "What is the API rate limit?" in user_prompt
    assert "The standard plan allows 1,000 requests per minute." in user_prompt


def test_prompt_contains_retrieved_source_and_content():
    messages = build_citation_faithfulness_messages(
        user_question="What is the API rate limit?",
        generated_answer="The standard plan allows 1,000 requests per minute.",
        retrieved_sources=[
            {
                "source": "api_usage_policy",
                "content": "The standard plan allows 1,000 requests per minute.",
            }
        ],
    )

    user_prompt = messages[1]["content"]

    assert "api_usage_policy" in user_prompt
    assert "The standard plan allows 1,000 requests per minute." in user_prompt


class FakeUsage:
    prompt_tokens = 100
    completion_tokens = 25
    total_tokens = 125


class FakeMessage:
    content = """
    {
        "verdict": "SUPPORTED",
        "reason": "The generated answer is directly supported by the supplied evidence.",
        "unsupported_claims": []
    }
    """


class FakeChoice:
    message = FakeMessage()


class FakeResponse:
    usage = FakeUsage()
    choices = [FakeChoice()]


class FakeCompletions:
    def create(self, **kwargs):
        return FakeResponse()


class FakeChat:
    completions = FakeCompletions()


class FakeClient:
    chat = FakeChat()


def test_citation_judge_returns_structured_result():
    judge = CitationFaithfulnessJudge(
        api_key="fake-key",
        model="fake-model",
    )

    judge.client = FakeClient()

    result = judge.evaluate(
        user_question="What is the API rate limit?",
        generated_answer=(
            "The standard plan allows 1,000 requests per minute."
        ),
        retrieved_sources=[
            {
                "source": "api_usage_policy",
                "content": (
                    "The standard plan allows 1,000 requests per minute."
                ),
            }
        ],
        expected_sources=["api_usage_policy"],
    )

    assert result.verdict == CitationFaithfulnessVerdict.SUPPORTED
    assert result.unsupported_claims == []
    assert result.reason


def test_citation_judge_tracks_usage():
    judge = CitationFaithfulnessJudge(
        api_key="fake-key",
        model="fake-model",
    )

    judge.client = FakeClient()

    judge.evaluate(
        user_question="What is the API rate limit?",
        generated_answer="The standard plan allows 1,000 requests per minute.",
        retrieved_sources=[
            {
                "source": "api_usage_policy",
                "content": "The standard plan allows 1,000 requests per minute.",
            }
        ],
    )

    assert judge.call_count == 1
    assert judge.total_prompt_tokens == 100
    assert judge.total_completion_tokens == 25
    assert judge.total_tokens == 125