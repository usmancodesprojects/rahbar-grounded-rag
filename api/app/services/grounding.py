"""Validate provenance and verify every displayed excerpt against its source."""
import re

from ..schemas import Answer, Citation, Passage

INJECTION = re.compile(
    r"ignore.{0,80}(instructions|previous|system|prompt)|"
    r"(system|developer)\s*(prompt|message)|"
    r"disregard.{0,80}(instructions|context)|override.{0,50}instructions",
    re.I | re.S,
)


def abstention(message: str = "The indexed corpus does not provide enough evidence to answer.") -> Answer:
    return Answer(reasoning="", answer=message, citations=[],
                  answered_from_context=False, confidence="low")


def normalize(text: str) -> str:
    punctuation = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
    return " ".join(text.translate(punctuation).split()).casefold()


def grounded(answer: Answer, passages: list[Passage]) -> Answer | None:
    if not answer.answered_from_context:
        return answer if not answer.citations else None
    if not answer.citations or not answer.answer.strip():
        return None
    evidence = []
    for citation in answer.citations:
        matches = [p for p in passages if p.source == citation.source
                   and p.section == citation.section
                   and (citation.page is None or p.page == citation.page)]
        if not matches:
            return None
        evidence.extend(matches)
    rendered = []
    used: dict[tuple[str, str, int | None], Citation] = {}
    for line in filter(str.strip, answer.answer.splitlines()):
        excerpt, sep, label = line.strip().rpartition(" [")
        quote = (excerpt if sep else line).strip(' "“”')
        if len(quote) < 8 or INJECTION.search(quote):
            return None
        pattern = rf"(?<!\w){re.escape(normalize(quote).removesuffix('.'))}(?!\w)"
        supporting = next((p for p in evidence
                           if (not sep or label == f"{p.source} / {p.section}]")
                           and re.search(pattern, normalize(p.text))), None)
        if supporting is None:
            return None
        rendered.append(f"{quote} [{supporting.source} / {supporting.section}]")
        key = supporting.source, supporting.section, supporting.page
        used[key] = Citation(source=supporting.source, section=supporting.section, page=supporting.page)
    return answer.model_copy(update={"answer": "\n".join(rendered), "citations": list(used.values())})
