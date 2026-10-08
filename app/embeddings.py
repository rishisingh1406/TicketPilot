import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class EmbeddingModel:
    def __init__(self):
        gemini_api_key = os.environ["GEMINI_API_KEY"]

        self.client = genai.Client(
            api_key=gemini_api_key
        )

        self.model = "gemini-embedding-2"
        self.dimensions = 768

    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("text must not be empty")

        result = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=self.dimensions
            ),
        )

        embedding = result.embeddings[0].values

        if len(embedding) != self.dimensions:
            raise RuntimeError(
                f"Expected embedding dimension {self.dimensions}, "
                f"got {len(embedding)}"
            )

        return embedding