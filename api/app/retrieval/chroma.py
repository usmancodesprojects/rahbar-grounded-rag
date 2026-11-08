"""Read a published Chroma snapshot and enforce the embedding pin."""
from __future__ import annotations

import logging
import math
import re
from typing import Any

import httpx

from ..config import Settings
from ..schemas import Passage

log = logging.getLogger(__name__)


def version_filter(question: str) -> dict[str, Any]:
    match = re.search(r"\b(?:19|20)\d{2}(?:-\d{2})?\b", question)
    if not match:
        archived = re.search(
            r"\b(old|older|previous|superseded|archived|repealed)\s+"
            r"(undergraduate\s+)?(rules|policy|version|handbook|edition)\b", question, re.I
        )
        return {"superseded": bool(archived)}
    version = match[0]
    year = version[:4]
    versions = [year, *(f"{year}-{month:02}" for month in range(1, 13)),
                f"{year}-{(int(year) + 1) % 100:02}"]
    if version != year:
        versions = [version]
    return {"doc_version": {"$in": versions}}


class ChromaRetriever:
    name = "chroma"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: Any = None

    def snapshot(self) -> Any:
        if self.client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.client = chromadb.HttpClient(
                host=self.settings.chroma_host, port=self.settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        pointer = self.client.get_collection(self.settings.collection, embedding_function=None)
        metadata = pointer.metadata or {}
        collection = pointer
        if metadata.get("active_collection"):
            collection = self.client.get_collection(metadata["active_collection"],
                                                    embedding_function=None)
            metadata = collection.metadata or {}
        actual = metadata.get("embed_model")
        if actual != self.settings.embed_model:
            log.warning("embedding pin mismatch", extra={"index_model": actual,
                        "api_model": self.settings.embed_model})
            raise ValueError(f"embedding pin mismatch: index={actual}, API={self.settings.embed_model}")
        if not metadata.get("dimension") or not collection.count():
            raise ValueError("index has no dimension or contains no passages")
        return collection

    def embed(self, question: str, dimension: int) -> list[float]:
        input_text = (f"search_query: {question}"
                      if self.settings.embed_model.startswith("nomic-embed-text") else question)
        response = httpx.post(f"{self.settings.ollama_url.rstrip('/')}/api/embed",
                              json={"model": self.settings.embed_model, "input": [input_text],
                                    "truncate": False}, timeout=httpx.Timeout(25, connect=3))
        response.raise_for_status()
        data = response.json()
        vector: list[float] = data["embeddings"][0]
        if (data.get("model") != self.settings.embed_model or len(vector) != dimension
                or not all(math.isfinite(value) for value in vector)):
            raise ValueError("query embedding violates the index pin")
        return vector

    def query(self, collection: Any, question: str, vector: list[float], k: int) -> list[Passage]:
        hits = collection.query(query_embeddings=[vector], where=version_filter(question),
                                n_results=k, include=["documents", "metadatas", "distances"])
        return [
            Passage(chunk_id=key, text=text, source=meta["source"], section=meta["section"],
                    page=meta["page"], score=1 - distance)
            for key, text, meta, distance in zip(
                hits["ids"][0], hits["documents"][0], hits["metadatas"][0], hits["distances"][0],
                strict=True
            )
        ]

    def retrieve(self, question: str, k: int) -> list[Passage]:
        collection = self.snapshot()
        return self.query(collection, question, self.embed(question, collection.metadata["dimension"]), k)
