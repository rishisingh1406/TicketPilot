import os

from dotenv import load_dotenv

from app.llm import GroqLLM


def create_llm() -> GroqLLM:
    load_dotenv()

    return GroqLLM(
        api_key=os.environ["GROQ_API_KEY"],
        model="qwen/qwen3.8-27b",
    )