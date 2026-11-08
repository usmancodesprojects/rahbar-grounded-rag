#!/usr/bin/env bash
set -euo pipefail
manifest=${1:-k8s/overlays/dev}
kubectl apply -k "$manifest"
kubectl -n rahbar create configmap fixture-embed --from-file=eval/fixture_embed.py
kubectl apply -f k8s/support/fixture-embed.yaml
kubectl -n rahbar patch configmap rahbar-config --type merge -p \
  '{"data":{"EMBED_MODEL":"fixture-hash-v1","LLM_PROVIDER":"stub","RELEVANCE_FLOOR":"0.13","OLLAMA_URL":"http://fixture-embed:11434"}}'
kubectl -n rahbar rollout restart deployment/api
kubectl -n rahbar rollout status deployment/fixture-embed --timeout=180s
kubectl -n rahbar rollout status statefulset/chroma --timeout=180s
bash scripts/load_corpus.sh eval/fixtures
kubectl -n rahbar patch job indexer --type merge -p '{"spec":{"suspend":false}}'
kubectl -n rahbar wait --for=condition=complete job/indexer --timeout=180s
kubectl -n rahbar rollout status deployment/api --timeout=240s
kubectl -n rahbar rollout status deployment/ui --timeout=180s
