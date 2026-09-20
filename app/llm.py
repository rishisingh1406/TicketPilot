import json

from groq import Groq

from schemas import AgentResponse


class GroqLLM:

    def __init__(self, api_key, model):
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, messages):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_response",
                    "schema": AgentResponse.model_json_schema(),
                },
            },
        )

        content = response.choices[0].message.content

        data = json.loads(content)

        return AgentResponse.model_validate(data)