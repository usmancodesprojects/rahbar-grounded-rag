"""Batch embedding calls and reject incomplete or inconsistent responses."""
from __future__ import annotations

import math

import httpx

from .config import IndexerSettings


def embed(texts: list[str], settings: IndexerSettings) -> list[list[float]]:
    vectors: list[list[float]] = []
    with httpx.Client(timeout=httpx.Timeout(120, connect=5)) as client:
        for start in range(0, len(texts), 16):
            batch = texts[start:start + 16]
            if settings.embed_model.startswith("nomic-embed-text"):
                batch = [f"search_document: {text}" for text in batch]
            response = client.post(f"{settings.ollama_url.rstrip('/')}/api/embed",
                                   json={"model": settings.embed_model, "input": batch,
                                         "truncate": False})
            response.raise_for_status()
            data = response.json()
            if data.get("model") != settings.embed_model:
                raise ValueError("embedding endpoint returned a different model")
            result = data["embeddings"]
            if len(result) != len(batch):
                raise ValueError("embedding endpoint returned an incomplete batch")
            for row in result:
                if (not row or not all(math.isfinite(value) for value in row)
                        or (vectors and len(row) != len(vectors[0]))):
                    raise ValueError("embedding endpoint returned an invalid vector")
                vectors.append(row)
    return vectors
