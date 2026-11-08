"""Question endpoint used by the same-origin chat UI."""
from fastapi import APIRouter, Header, Request, Response

from ..schemas import AskRequest, AskResponse
from ..services.answer import answer_question

router = APIRouter(prefix="/api")


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request, response: Response,
        x_session_id: str | None = Header(default=None, pattern=r"^[A-Za-z0-9_-]{24,80}$")) -> AskResponse:
    state = request.app.state
    result = answer_question(body.question, state.retriever, state.provider, state.settings,
                             state.cache, x_session_id)
    response.headers["X-Cache"] = "HIT" if result.cached else "MISS"
    return result
