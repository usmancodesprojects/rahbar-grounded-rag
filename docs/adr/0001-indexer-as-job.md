# ADR 0001 · Indexer as a Job

Accepted. Starting the indexer in three API replicas would duplicate extraction and embedding, race to publish incomplete data and make rollouts pay the batch cost.

The Job owns retries and completion, while readiness keeps requests off readers until an index exists. The indexer stages a complete immutable collection, checks its count and updates one pointer. The previous index stays available during re-indexing. Overlapping manual and scheduled Jobs can publish only complete generations. The last publication wins. Avoid overlapping different corpus revisions and prune retired generations after requests drain.
