"""Prometheus metrics at /metrics (section 4.8).

Request count and latency are wired up already. Add your own the same way:
retrieval latency, generation latency, cache hits, abstentions, fallbacks, tokens.
"""

from __future__ import annotations

from contextvars import ContextVar

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

router = APIRouter()

REQUESTS = Counter("rahbar_requests_total", "HTTP requests", ["path", "status"])
LATENCY = Histogram(
    "rahbar_request_seconds",
    "HTTP request latency",
    ["path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)


STAGE = Histogram("rahbar_stage_seconds", "Pipeline stage latency", ["stage"])
CACHE = Counter("rahbar_cache_total", "Semantic cache lookups", ["result"])
ABSTENTIONS = Counter("rahbar_abstentions_total", "Abstained answers")
FALLBACKS = Counter("rahbar_fallbacks_total", "Safe fallbacks")
TOKENS = Histogram("rahbar_model_tokens", "Provider tokens per API request", ["direction"],
                   buckets=(16, 64, 128, 256, 512, 1024, 2048, 4096))


REQUEST_TOKENS: ContextVar[list[int] | None] = ContextVar("request_tokens", default=None)


def record_tokens(input_tokens: int, output_tokens: int) -> None:
    usage = REQUEST_TOKENS.get()
    if usage is not None:
        usage[0] += input_tokens
        usage[1] += output_tokens


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
