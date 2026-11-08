"""Remove repeated page margins and extraction artifacts."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace

from .models import Document


def clean(doc: Document) -> Document:
    lines = [[line.strip() for line in page.text.splitlines()] for page in doc.pages]
    margins = Counter(line for page in lines for line in set(page[:2] + page[-2:])
                      if line and not re.match(r"^(#|\d+\.)", line))
    repeated = {line for line, count in margins.items()
                if count >= 3 and count / len(lines) >= 0.6}
    pages = []
    for page, content in zip(doc.pages, lines, strict=True):
        kept = [line for i, line in enumerate(content)
                if not ((i < 2 or i >= len(content) - 2)
                        and (line in repeated or re.fullmatch(r"\d+", line)))]
        text = "\n".join(kept).replace("\u00ad", "").replace("\u00a0", " ")
        text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)
        pages.append(replace(page, text=text.strip()))
    return replace(doc, pages=pages)
