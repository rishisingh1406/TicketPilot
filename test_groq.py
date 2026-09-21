import os

from dotenv import load_dotenv

from app.llm import GroqLLM


load_dotenv()


messages = [
    {
        "role": "system",
        "content": """
You are a support agent.

You must return a structured AgentResponse.

Rules:

- TOOL_CALL:
  - tool must be RAG
  - tool_input is required
  - user_message must be null
  - support_message must be null

- ANSWER:
  - tool must be null
  - tool_input must be null
  - user_message is required
  - support_message must be null

- ESCALATE:
  - tool must be null
  - tool_input must be null
  - user_message is required
  - support_message is required

For ESCALATE:
- user_message is the message intended for the customer.
- support_message is the explanation/context intended for the human support team.
""",
    },
    {
        "role": "user",
        "content": "I was charged twice for my subscription.",
    },
]


llm = GroqLLM(
    api_key=os.environ["GROQ_API_KEY"],
    model="qwen/qwen3.8-27b",
)


response = llm.generate(messages)


print("Response type:")
print(type(response))

print("\nResponse:")
print(response)

print("\nAction:")
print(response.action)

print("\nTool:")
print(response.tool)

print("\nTool input:")
print(response.tool_input)

print("\nUser message:")
print(response.user_message)

print("\nSupport message:")
print(response.support_message)