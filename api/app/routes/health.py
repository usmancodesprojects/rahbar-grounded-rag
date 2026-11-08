"""Dependency-free liveness and dependency-aware readiness."""
from fastapi import APIRouter, Request, Response

from ..retrieval.chroma import ChromaRetriever

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, object]:
    state = request.app.state
    checks = {}
    if isinstance(state.retriever, ChromaRetriever):
        try:
            state.retriever.snapshot()
            checks["chroma"] = "ok"
        except Exception as exc:
            checks["chroma"] = str(exc) if isinstance(exc, ValueError) else "unavailable"
            response.status_code = 503
    if state.cache:
        try:
            state.cache.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
            response.status_code = 503
    return {"status": "not ready" if response.status_code == 503 else "ready", "checks": checks}
