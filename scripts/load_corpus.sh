#!/usr/bin/env bash
set -euo pipefail
root=${1:-corpus/raw}
namespace=rahbar
pod=corpus-loader
[[ -d "$root" ]] || { echo "Missing corpus directory: $root" >&2; exit 1; }
trap 'kubectl -n "$namespace" delete pod "$pod" --ignore-not-found --wait=false' EXIT
kubectl -n "$namespace" apply -f k8s/support/corpus-loader.yaml
kubectl -n "$namespace" wait --for=condition=Ready "pod/$pod" --timeout=120s
kubectl -n "$namespace" cp "$root/." "$pod:/corpus"
