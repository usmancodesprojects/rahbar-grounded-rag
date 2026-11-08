"""Publish a complete immutable index through one metadata pointer."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from .config import IndexerSettings
from .models import Chunk


def get_client(settings: IndexerSettings) -> Any:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port,
                               settings=ChromaSettings(anonymized_telemetry=False))


def store(chunks: list[Chunk], vectors: list[list[float]], settings: IndexerSettings) -> int:
    if not chunks or len(chunks) != len(vectors):
        raise ValueError("refusing to publish an empty or incomplete index")
    client = get_client(settings)
    generation = uuid4().hex
    name = f"idx-{generation}"
    metadata = {"embed_model": settings.embed_model, "dimension": len(vectors[0]),
                "generation": generation}
    collection = client.create_collection(name, embedding_function=None,
                                          metadata={**metadata, "hnsw:space": "cosine"})
    for start in range(0, len(chunks), 100):
        batch = chunks[start:start + 100]
        collection.add(ids=[c.id for c in batch], documents=[c.text for c in batch],
                       metadatas=[c.metadata() for c in batch],
                       embeddings=vectors[start:start + len(batch)])
    count = int(collection.count())
    if count != len(chunks):
        raise RuntimeError("staged index count differs from corpus chunk count")
    pointer = client.get_or_create_collection(settings.collection, embedding_function=None)
    pointer.modify(metadata={**metadata, "active_collection": name})
    return count
