#!/usr/bin/env bash
set -euo pipefail
kubectl label nodes --all ingress-ready=true --overwrite
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.8/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=180s
# The manifest garbage-collects the admission Jobs after completion.
for attempt in {1..60}; do
  bundle=$(kubectl get validatingwebhookconfiguration ingress-nginx-admission \
    -o jsonpath='{.webhooks[0].clientConfig.caBundle}')
  if [[ -n "$bundle" ]]; then
    exit 0
  fi
  sleep 2
done
echo "Ingress admission CA was not installed" >&2
exit 1
