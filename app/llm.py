import json

from groq import Groq

from schemas import AgentLLMResponse


class GroqLLM:

    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0

    def reset_usage(self) -> None:
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0

    def generate(self, messages: list[dict]) -> AgentLLMResponse:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1200,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_response",
                    "strict": True,
                    "schema": AgentLLMResponse.model_json_schema(),
                },
            },
        )

        usage = response.usage
        choice = response.choices[0]

        # Track token usage
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.call_count += 1

        # Diagnostics
        print("LLM FINISH REASON:", choice.finish_reason)
        print("LLM PROMPT TOKENS:", usage.prompt_tokens)
        print("LLM COMPLETION TOKENS:", usage.completion_tokens)
        print("LLM TOTAL TOKENS:", usage.total_tokens)

        content = choice.message.content

        if not content:
            raise RuntimeError("LLM returned empty content")

        print("RAW LLM CONTENT:")
        print(content)

        # Detect output truncation before attempting JSON parsing
        if choice.finish_reason == "length":
            raise RuntimeError(
                "LLM response was truncated because it reached max_tokens"
            )

        try:
            data = json.loads(content)

        except json.JSONDecodeError as e:
            print("AGENT LLM JSON PARSE ERROR:")
            print(type(e).__name__)
            print(e)

            print("INVALID LLM CONTENT:")
            print(content)

            raise RuntimeError(
                "LLM returned invalid JSON"
            ) from e

        try:
            return AgentLLMResponse.model_validate(data)

        except Exception as e:
            print("AGENT LLM VALIDATION ERROR:")
            print(type(e).__name__)
            print(e)

            print("VALIDATION INPUT:")
            print(data)

            raise
