"""Shared, bounded semantic cache and short-lived session turns."""
import json
import math
import re
from typing import Any

from ..schemas import AskResponse

FOLLOW_UP = re.compile(
    r"^\s*(and\b|what about\b|how about\b|why[?.!\s]*$|why (is that|not)\b|can (i|they) do (it|that)\b)",
    re.I,
)
SENSITIVE = re.compile(r"\b(?:\d+(?:[.-]\d+)*|not|no|without|except|before|after|"
                       r"minimum|maximum|old|older|previous|superseded|archived|repealed|current|[a-z]{2,}\d+)\b", re.I)


def scope(question: str) -> list[str]:
    return SENSITIVE.findall(question.lower())


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return -1
    denominator = math.sqrt(sum(x*x for x in a) * sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b, strict=True)) / denominator if denominator else -1


class Cache:
    def __init__(self, url: str) -> None:
        from redis import Redis

        self.redis: Any = Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)

    def ping(self) -> None:
        self.redis.ping()

    def lookup(self, key: str, question: str, vector: list[float], threshold: float) -> AskResponse | None:
        best = None
        best_score = threshold
        for raw in self.redis.lrange(key, 0, 99):
            row = json.loads(raw)
            if row["scope"] != scope(question):
                continue
            score = cosine(vector, row["vector"])
            if score >= best_score:
                best = AskResponse.model_validate(row["response"])
                best_score = score
        return best

    def store(self, key: str, question: str, vector: list[float], response: AskResponse) -> None:
        with self.redis.pipeline() as pipe:
            pipe.lpush(key, json.dumps({"scope": scope(question), "vector": vector,
                                        "response": response.model_dump(exclude={"request_id"}) |
                                        {"request_id": ""}}))
            pipe.ltrim(key, 0, 99)
            pipe.expire(key, 1800)
            pipe.execute()

    def previous(self, session: str) -> str:
        value: bytes | None = self.redis.get(f"rahbar:session:{session}")
        if not value:
            return ""
        try:
            turn = json.loads(value)
        except ValueError:
            return value.decode()  # Short-lived sessions written by older replicas.
        return str(turn.get("question", "")) if isinstance(turn, dict) else value.decode()

    def remember(self, session: str, question: str, response: AskResponse) -> None:
        turn = {"question": question, "answer": response.answer,
                "answered_from_context": response.answered_from_context}
        self.redis.setex(f"rahbar:session:{session}", 1800, json.dumps(turn))
