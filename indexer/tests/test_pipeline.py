"""Tests for stable IDs, metadata and overlap across bounded chunks."""
from pathlib import Path

from pipeline.chunk import chunk, windows
from pipeline.clean import clean
from pipeline.extract import extract


def test_fixture_metadata_and_section(tmp_path: Path) -> None:
    path = tmp_path / "version.md"
    path.write_text("---\ndoc_version: 2023\n---\n\n## 1. Attendance\n\n"
                    "1.1 Attendance is required.", encoding="utf-8")
    doc = clean(extract(str(path), "2023", True))
    first, = chunk(doc, 50, 5)
    assert first == chunk(doc, 50, 5)[0]
    assert first.metadata() == {"source": "version.md", "section": "1. Attendance", "page": 1,
                                "doc_version": "2023", "superseded": True}
    assert "doc_version" not in first.text


def test_long_sentence_sliding_window() -> None:
    pieces = list(windows("one two three four five six seven eight nine", 5, 2))
    assert pieces == ["one two three four five", "four five six seven eight", "seven eight nine"]
