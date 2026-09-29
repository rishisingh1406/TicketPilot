import json

from groq import Groq

from schemas import AgentResponse


class GroqLLM:

    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, messages: list[dict]) -> AgentResponse:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=800,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_response",
                    "strict": True,
                    "schema": AgentResponse.model_json_schema(),
                },
            },
        )

        content = response.choices[0].message.content

        data = json.loads(content)

        print("RAW MODEL DATA:")
        print(data)

        return AgentResponse.model_validate(data)