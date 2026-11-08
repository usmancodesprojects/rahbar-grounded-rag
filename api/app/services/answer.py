"""Coordinate retrieval, validation, abstention and shared cache."""
from __future__ import annotations

import logging
from typing import Any

from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..retrieval.base import Retriever
from ..retrieval.chroma import ChromaRetriever
from ..routes.metrics import ABSTENTIONS, CACHE, FALLBACKS, STAGE
from ..schemas import Answer, AskResponse, Passage, RetrievedRef
from .cache import FOLLOW_UP, Cache
from .grounding import INJECTION, abstention, grounded

log = logging.getLogger("rahbar.answer")


def generate(question: str, evidence: list[Passage], provider: LLMProvider) -> Answer:
    if not evidence or INJECTION.search(question):
        return abstention()
    retry_attempts = (1, 2)
    with STAGE.labels("generation").time():
        for attempt in retry_attempts:
            try:
                answer = Answer.model_validate(provider.generate(question, evidence), strict=True)
                if grounded(answer, evidence):
                    return answer if answer.answered_from_context else abstention()
                raise ValueError("invalid grounding")
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                log.warning("invalid generation", extra={"attempt": attempt, "kind": type(exc).__name__})
            except Exception as exc:
                log.warning("provider failed", extra={"kind": type(exc).__name__})
                break
    FALLBACKS.inc()
    return abstention("I could not verify an answer from the indexed evidence. Please try again.")


def report(response: AskResponse, settings: Settings) -> AskResponse:
    if not response.answered_from_context:
        ABSTENTIONS.inc()
    log.info("answered", extra={"provider": response.provider, "top_k": settings.top_k,
                               "chunk_ids": [p.chunk_id for p in response.retrieved],
                               "scores": [round(p.score, 4) for p in response.retrieved],
                               "abstention": not response.answered_from_context,
                               "cached": response.cached})
    return response


def answer_question(question: str, retriever: Retriever, provider: LLMProvider,
                    settings: Settings, cache: Cache | None = None,
                    session: str | None = None) -> AskResponse:
    rid = request_id_var.get()
    follow_up = bool(FOLLOW_UP.search(question))
    query = question
    passages: list[Passage] = []
    vector: list[float] = []
    key = ""
    skip_cache = follow_up or bool(INJECTION.search(question))
    answer = abstention()
    try:
        if follow_up and cache and session:
            prior = cache.previous(session)
            if prior:
                query = f"{prior} Follow-up: {question}"[:1000]
        if not follow_up or query != question:
            with STAGE.labels("retrieval").time():
                if isinstance(retriever, ChromaRetriever):
                    collection: Any = retriever.snapshot()
                    vector = retriever.embed(query, collection.metadata["dimension"])
                    key = (f"rahbar:cache:{collection.id}:{settings.llm_provider}:"
                           f"{settings.llm_model}:{settings.top_k}:{settings.relevance_floor}")
                    if cache and not skip_cache:
                        cached = cache.lookup(key, question, vector, settings.cache_threshold)
                        CACHE.labels("hit" if cached else "miss").inc()
                        if cached:
                            if session:
                                cache.remember(session, question)
                            return report(cached.model_copy(update={"request_id": rid, "cached": True}),
                                          settings)
                    passages = retriever.query(collection, query, vector, settings.top_k)
                else:
                    passages = retriever.retrieve(query, settings.top_k)
            evidence = [p for p in passages if p.score >= settings.relevance_floor
                        and not INJECTION.search(p.text)]
            answer = generate(query, evidence, provider)
    except Exception as exc:
        log.warning("query dependency failed", extra={"kind": type(exc).__name__})
        FALLBACKS.inc()
        answer = abstention("The evidence service is temporarily unavailable. Please try again.")
    response = AskResponse(
        request_id=rid, answer=answer.answer, citations=answer.citations,
        answered_from_context=answer.answered_from_context, confidence=answer.confidence,
        retrieved=[RetrievedRef.model_validate(p.model_dump()) for p in passages],
        provider=provider.name,
    )
    if cache:
        try:
            if key and not skip_cache and answer.answered_from_context and provider.name != "stub":
                cache.store(key, question, vector, response)
            if session and not follow_up and answer.answered_from_context:
                cache.remember(session, question)
        except Exception as exc:
            log.warning("cache write failed", extra={"kind": type(exc).__name__})
    return report(response, settings)
