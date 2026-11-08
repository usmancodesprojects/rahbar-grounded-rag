"""Validate provenance and verify every displayed excerpt against its source."""
import re

from ..schemas import Answer, Passage

INJECTION = re.compile(
    r"ignore.{0,80}(instructions|previous|system|prompt)|"
    r"(system|developer)\s*(prompt|message)|"
    r"disregard.{0,80}(instructions|context)|override.{0,50}instructions",
    re.I | re.S,
)


def abstention(message: str = "The indexed corpus does not provide enough evidence to answer.") -> Answer:
    return Answer(reasoning="", answer=message, citations=[],
                  answered_from_context=False, confidence="low")


def grounded(answer: Answer, passages: list[Passage]) -> bool:
    if not answer.answered_from_context:
        return not answer.citations
    if not answer.citations or not answer.answer.strip():
        return False
    keys = {(c.source, c.section, c.page) for c in answer.citations}
    evidence = [p for p in passages if (p.source, p.section, p.page) in keys]
    if keys != {(p.source, p.section, p.page) for p in evidence}:
        return False
    for line in filter(str.strip, answer.answer.splitlines()):
        excerpt, sep, label = line.strip().rpartition(" [")
        quote = " ".join(excerpt.strip(' "\u201c\u201d').split())
        if not sep or len(quote) < 8 or INJECTION.search(quote):
            return False
        if not any(label == f"{p.source} / {p.section}]" and
                   quote in " ".join(p.text.split()) for p in evidence):
            return False
    return True
