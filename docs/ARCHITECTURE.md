# Architecture

Ingress routes `/api` to three FastAPI replicas and `/` to nginx. Chroma and Redis use internal ClusterIP Services. Chroma runs as a one-replica StatefulSet so a replacement Pod keeps its identity and the PVC from `volumeClaimTemplates`. Redis persists its bounded cache and expiring session turns to a PVC, with a Recreate strategy for the single writer.

The one-shot Job and weekly CronJob share an image, config and read-only corpus mount. The indexer writes immutable Chroma generations and updates the pointer after checking the stored count. Readers pin each request to one generation. Cache entries are namespaced by generation and expire automatically. Prune retired Chroma generations in a maintenance window once in-flight requests drain.

Startup and liveness probe only the process. Readiness checks a non-empty index with the matching embedding model and verifies Redis connectivity. Rolling updates allow one surge Pod and zero unavailable Pods. Workloads have tokenless ServiceAccounts, non-root IDs, read-only root filesystems and dropped capabilities. NetworkPolicies allow only DNS, Ingress routes, the data paths and the Ollama port. A CNI such as Calico enforces those policies.
