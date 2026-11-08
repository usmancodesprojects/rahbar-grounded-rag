"""Pack sections into word-budgeted passages without crossing pages."""
from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator

from .models import Chunk, Document

HEADING = re.compile(r"^(?:#{1,6}\s+(.+)|(\d+(?:\.\d+)+\.?)\s+(.+)|"
                     r"(\d+\.\s+[A-Z][^\n]{2,90}))$")


def sections(text: str, section: str, markdown: bool) -> Iterator[tuple[str, str]]:
    lines: list[str] = []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match and (not markdown or match[1]):
            if any(lines):
                yield section, "\n".join(lines)
            section = match[1] or (match[2].rstrip(".") if match[2] else match[4])
            lines = [line.lstrip("# ")]
        else:
            lines.append(line)
    yield section, "\n".join(lines)


def windows(text: str, size: int, overlap: int) -> Iterator[str]:
    current: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        units = [paragraph] if len(paragraph.split()) <= size else re.split(
            r"(?<=[.!?])\s+(?=[A-Z])", paragraph
        )
        for unit in units:
            words = unit.split()
            if not words:
                continue
            if len(current) + len(words) > size and len(current) > overlap:
                yield " ".join(current)
                current = current[-overlap:] if overlap else []
            current.extend(words)
            while len(current) > size:
                yield " ".join(current[:size])
                current = current[size - overlap:]
    if current:
        yield " ".join(current)


def chunk(doc: Document, size: int, overlap: int) -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError("chunk overlap must be nonnegative and smaller than size")
    chunks: list[Chunk] = []
    section = "Overview"
    for page in doc.pages:
        for section, content in sections(page.text, section, doc.source.lower().endswith(".md")):
            for text in windows(content, size, overlap):
                key = f"{doc.source}\0{doc.doc_version}\0{page.page}\0{len(chunks)}\0{text}"
                chunks.append(Chunk(hashlib.sha256(key.encode()).hexdigest(), text, doc.source,
                                    section, page.page, doc.doc_version, doc.superseded))
    return chunks
