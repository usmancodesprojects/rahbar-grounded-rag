#!/usr/bin/env bash
set -euo pipefail
kubectl label nodes --all ingress-ready=true --overwrite
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.8/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=180s
kubectl -n ingress-nginx wait --for=condition=complete job/ingress-nginx-admission-patch --timeout=180s
