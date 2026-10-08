import os

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()


class EmbeddingModel:
    def __init__(self):
        hf_token = os.environ["HF_TOKEN"]

        self.client = InferenceClient(
            provider="hf-inference",
            api_key=hf_token,
        )

        self.model = "BAAI/bge-small-en-v1.5"
        self.dimensions = 384

    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("text must not be empty")

        embedding = self.client.feature_extraction(
            text,
            model=self.model,
        )

        embedding = embedding.squeeze().tolist()

        if len(embedding) != self.dimensions:
            raise RuntimeError(
                f"Expected embedding dimension {self.dimensions}, "
                f"got {len(embedding)}"
            )

        return embedding