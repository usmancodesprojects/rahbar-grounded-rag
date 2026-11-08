# ADR 0004 · Provider and data governance

Accepted. Host Ollama keeps questions and passages on the machine serving the cluster. Temperature 0.1 favors stable selection and JSON. CPU-only verification favored the pinned `llama3.2:1b` model. Ollama selects a numbered excerpt or abstains using a schema derived from `Answer`. The application resolves that choice to an exact quote and canonical citation. Pydantic validates the response against the underlying Answer model. The API also checks citation tuples and exact excerpt support.

Hosted mode sends questions and selected evidence to a third party. Enable it only for a permitted corpus and endpoint, with HTTPS and a Kubernetes Secret. Logs contain identifiers, scores and operational metadata. Session context is optional and expires.
