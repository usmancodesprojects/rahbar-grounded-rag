# ADR 0002 · Chunking and embedding

Accepted. Keep physical pages and section boundaries for provenance. Use paragraph and sentence boundaries before falling back to overlapping word windows. Preserve exact codes and table cells.

Pin `nomic-embed-text:v1.5` in both workloads and record model and dimension alongside the generation. Prefix document and query inputs with the Nomic retrieval tasks. A change of pin requires a complete rebuild and coordination with API configuration. Sparse ranking could complement embeddings for exact identifiers.
