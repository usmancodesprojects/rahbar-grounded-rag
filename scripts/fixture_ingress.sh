#!/usr/bin/env bash
set -euo pipefail
# Port-forward the controller in CI. Requests still cross the real Ingress rules.
kubectl -n ingress-nginx port-forward service/ingress-nginx-controller 18080:80 &
forward=$!
trap 'kill "$forward" 2>/dev/null || true' EXIT
for attempt in {1..30}; do
  if curl -fsS -H 'Host: rahbar.local' http://127.0.0.1:18080/ >/dev/null; then
    python eval/run_eval.py --api http://127.0.0.1:18080 --host rahbar.local \
      --golden eval/fixtures/golden.fixture.yaml --baseline eval/fixtures/baseline.json \
      --out fixture-results.json
    exit
  fi
  sleep 2
done
exit 1
