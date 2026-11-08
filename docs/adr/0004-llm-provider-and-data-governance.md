# ADR 0004 · Provider and data governance

Accepted. Host Ollama keeps questions and passages on the machine serving the cluster. Temperature 0.1 favors stable excerpts and JSON. Pydantic validates the same schema sent to the provider. The API also checks citation tuples and exact excerpt support.

Hosted mode sends questions and selected evidence to a third party. Enable it only for a permitted corpus and endpoint, with HTTPS and a Kubernetes Secret. Logs contain identifiers, scores and operational metadata. Session context is optional and expires.
