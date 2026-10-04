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
            max_tokens=800,
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

        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.call_count += 1

        content = response.choices[0].message.content

        data = json.loads(content)

        try:
            return AgentLLMResponse.model_validate(data)

        except Exception as e:
            print("AGENT LLM VALIDATION ERROR:")
            print(type(e).__name__)
            print(e)

            print("VALIDATION INPUT:")
            print(data)

            raise
