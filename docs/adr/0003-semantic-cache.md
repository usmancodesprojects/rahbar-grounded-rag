# ADR 0003 · Redis semantic cache

Accepted. Redis shares up to 100 scored candidates per generation and config across API replicas. Keeping cache writes in Redis lets the API consume Chroma in read-only mode. Lookup uses cosine similarity and rejects candidates with different numeric, temporal or negation scope. Follow-ups, abstentions and failed validation are excluded.

Cache keys switch with the active Chroma collection ID, so re-indexing immediately invalidates prior answers. Redis expires inactive keys after 30 minutes. A threshold and scope guard reduce ambiguity. An equivalent-sounding question can still have a different intent.
