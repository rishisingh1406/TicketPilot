import json

from django.http import response
from groq import Groq

from schemas import AgentLLMResponse


class GroqLLM:

    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

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
        print("FINISH REASON:", response.choices[0].finish_reason)
        print("USAGE:", response.usage)
        content = response.choices[0].message.content

        data = json.loads(content)

        print("RAW MODEL DATA:")
        print(data)

        return AgentLLMResponse.model_validate(data)