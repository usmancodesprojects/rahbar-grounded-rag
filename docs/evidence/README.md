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
