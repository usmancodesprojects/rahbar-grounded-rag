# Engineering notes

1. With three readers, startup indexing would multiply extraction and embedding work and let concurrent writers expose mixed or incomplete states. The batch object isolates writes. [Job parallelism and retry limit](../k8s/base/indexer-job.yaml#L5-L9) and the [single publication point](../indexer/pipeline/store.py#L19) keep serving separate from batch completion.
2. If Chroma-backed readiness became liveness, three failed 20-second checks during a 90-second stall could restart all replicas. Process-only readiness would advertise replicas even though none can retrieve. The configured probes instead remove unavailable readers from the Service and let them recover once Chroma responds. [Manifest probes](../k8s/base/api.yaml#L59) and [handlers](../api/app/routes/health.py#L10).
3. The HPA measures API container CPU as a percentage of its CPU request. The API spends much of a model call waiting on I/O. A sustained generation backlog or in-flight requests per available inference slot would better measure saturation. Export that gauge, install a Prometheus adapter for the custom metrics API and set HPA targets against measured throughput. A separate upper bound is needed when the single Ollama backend saturates. [API resource requests](../k8s/base/api.yaml#L42) and [HPA](../k8s/base/hpa.yaml#L10).
4. In four `kubectl top` samples taken during the real indexing Job, indexer memory reached 178 MiB. The 1 GiB limit gives 846 MiB of headroom over that sampled peak. The 256 MiB request covers observed extraction plus headroom for vectors and library startup. Indexer CPU reached 866m in a separate sample. A 750m request and 2-core cap let the batch Pod make progress without monopolizing a four-core cluster. Exceeding the memory limit leads to an OOMKill, commonly exit 137. [Resource samples](evidence/kubectl-top.txt) and [Job manifest](../k8s/base/indexer-job.yaml#L39).
5. Compare the by-type recall groups in the evaluation results. A clause-number question has few semantic anchors, and an unrelated paragraph can embed closer than the exact clause. Sparse BM25 or an exact clause metadata match followed by rank fusion can complement dense retrieval. [Ranking and metadata filter](../api/app/retrieval/chroma.py#L17).
6. If only the API restarts with a different embedding model, it logs the index and API pins, returns 503 from readiness and refuses retrieval. The previous API ReplicaSet can continue serving with the matching pin while the new rollout is stuck. Without the check, compatible vector dimensions could return incorrect nearest neighbours with an apparently healthy endpoint. [Snapshot guard](../api/app/retrieval/chroma.py#L40) and [readiness handler](../api/app/routes/health.py#L15).
7. On this host, Docker initially appeared unable to install Python dependencies. The build log identified a certificate trust failure before package resolution. The same proxy CA worked through Windows trust but was missing inside the Linux build. The optional BuildKit CA mount lets the verified local bundle supply trust during installation without packaging it in the image. Kubernetes later showed the analogous registry problem as `ImagePullBackOff`. `kubectl get events -A --sort-by=.lastTimestamp` distinguished a registry TLS error from a missing application tag. [Build trust configuration](../api/Dockerfile#L5).


## Resource observations

| Container | Observed Kubernetes sample | Shipped requests and limits |
| --- | --- | --- |
| API | 28m CPU and 68 MiB maximum across the four samples | 100m/192 MiB request leaves room for imports and concurrent JSON handling. 1 CPU/512 MiB bounds a replica. |
| UI | 1m and 2 MiB | 25m/32 MiB request and 200m/96 MiB limit allow simultaneous connections and nginx startup. |
| Chroma | 22m and 22 MiB while serving the fixture index | 200m/256 MiB request and 2 CPU/1 GiB limit allow graph construction and a larger index. |
| Redis | 150m and 6 MiB | 150m/96 MiB request matches sampled CPU and the configured cache cap. 500m/256 MiB permits AOF rewrite overhead. |
| Indexer | 178 MiB sampled peak during real extraction | 750m/256 MiB request and 2 CPU/1 GiB limit. |
| Corpus loader | Short-lived transfer Pod | 10m/16 MiB request and 100m/48 MiB limit for a single tar copy. |
| Fixture embedding double | 9m and 15 MiB | 25m/32 MiB request and 250m/128 MiB limit for small fixture batches. |

These are single-machine samples. The HPA showed three replicas and a numeric utilization target. Measure production peak concurrency separately. [HPA output](evidence/hpa.txt)
