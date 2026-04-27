import numpy as np
import ollama


class LLMClient:
    def __init__(self, model: str):
        self.model = model

    def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = ollama.chat(model=self.model, messages=messages)
        return response["message"]["content"]


class EmbeddingClient:
    def __init__(self, model: str):
        self.model = model

    def embed(self, text: str) -> np.ndarray:
        response = ollama.embeddings(model=self.model, prompt=text)
        return np.array(response["embedding"], dtype=np.float32)

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.dot(a, b) / denom) if denom else 0.0
