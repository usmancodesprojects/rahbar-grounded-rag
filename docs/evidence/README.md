# Verification evidence

This directory records observed output. Local kind runs are separate from GitHub Actions and the Minikube setup instructions. The public repository exposes the checks and review state. [GitHub repository](https://github.com/usmancodesprojects/rahbar-grounded-rag)


| Evidence | Artifact |
| --- | --- |
| Protected main requires one review and CI | [Branch protection](branch-protection.json) |
| Kubernetes fixture Job created 13 chunks | [Indexer log](fixture-indexer.txt) |
| Three ready API endpoints and a running UI | [Service endpoints](api-endpoints.txt) and [Pod listing](kind-pods.txt) |
| Kubernetes Ingress fixture gate | [Scores](kind-fixture-eval.json) and [UI screenshot](fixture-chat.jpg) |
| Deliberate top-one regression | [Live fixture gate output](fixture-gate-failure.txt) |
| API Pod replacement and visible UI rollback | [Rollout transcript](rollout-and-replacement.txt) |
| Kubernetes resource use and HPA | [Resource samples](kubectl-top.txt) and [HPA status](hpa.txt) |
| Real-corpus chunk and cache comparison | [Measured configurations](chunk-and-cache-measurements.json) |

| GitHub Actions rejected top-one retrieval | [Failed regression run](https://github.com/usmancodesprojects/rahbar-grounded-rag/actions/runs/42469021118) and [gate log](github-regression.txt) |
| Embedding pin mismatch withheld the new replica | [Readiness transcript](embedding-pin.txt) |
| Measured real snapshot restored and served by three API replicas | [Restore Job](real-index-restore.txt) and [API endpoints](real-api-endpoints.txt) |
| Coursework submission checker | [Checker output](submission-check.txt) |

The final 15-question run went through kind Ingress using the 1,024-chunk university snapshot, Nomic embeddings and Ollama. Recall@3 and recall@5 were both 84.62%. All returned citations matched retrieved evidence, and all required refusals passed. The model answered three questions. Both exact-clause questions missed their expected sections.

The first in-cluster raw-corpus Job timed out reaching Ollama with the original host egress address. After correcting the local route and verifying it from an API Pod, the demonstration restored the snapshot built with the full pipeline against standalone Chroma. The fixture suite exercised the complete indexing Job inside kind. The Minikube instructions are provided for a fresh install.
