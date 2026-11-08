"""Measure chunking, nearest neighbours and cache threshold candidates.

Run with PYTHONPATH=api:indexer and the same Ollama model as the cluster.
The optional extraction snapshot stays local because it contains source text.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from app.config import get_settings as api_settings
from app.retrieval.chroma import ChromaRetriever, version_filter
from app.services.cache import cosine, scope
from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.config import get_settings
from pipeline.embed import embed
from pipeline.extract import extract
from pipeline.models import Document, Page
from pipeline.run import discover
from run_eval import average, load_golden, recall_at_k

PAIRS = [
    (True, "What minimum CGPA avoids academic warning?", "What CGPA avoids academic warning?"),
    (True, "What is the minimum CGPA for graduation?", "What is the required graduation CGPA?"),
    (False, "What minimum CGPA avoids academic warning?", "What minimum CGPA is needed to graduate?"),
    (False, "How many weeks are in a regular semester?", "How many weeks are in a summer semester?"),
    (False, "Can I drop a course during the first semester?", "Can I drop a course during the summer semester?"),
    (False, "What is the refund for dropping a course?", "What is the refund for withdrawing from a course?"),
]


def documents(snapshot: Path) -> list[Document]:
    if snapshot.exists():
        return [
            Document(row["source"], row["doc_version"], row["superseded"],
                     [Page(**page) for page in row["pages"]])
            for row in json.loads(snapshot.read_text(encoding="utf-8"))
        ]
    result = []
    for path, version, superseded in discover(get_settings().corpus_dir):
        doc = clean(extract(str(path), version, superseded))
        print(doc.source, len(doc.pages), "pages", sum(page.ocr for page in doc.pages), "OCR", flush=True)
        result.append(doc)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps([asdict(doc) for doc in result]), encoding="utf-8")
    return result


def eligible(meta: dict, question: str) -> bool:
    filt = version_filter(question)
    if "superseded" in filt:
        return not meta["superseded"]
    return meta["doc_version"] in filt["doc_version"]["$in"]


def run(docs: list[Document], golden: Path, out: Path) -> None:
    settings = get_settings()
    reader = ChromaRetriever(api_settings())
    questions = load_golden(golden)
    queries = {row["question"] for row in questions} | {q for _, a, b in PAIRS for q in (a, b)}
    vectors = {q: reader.embed(q, 768) for q in sorted(queries)}
    source_words = sum(len(p.text.split()) for doc in docs for p in doc.pages)
    report: dict = {"source_words": source_words, "settings": []}
    embedded: dict[str, list[float]] = {}
    for size, overlap in ((200, 25), (400, 50), (650, 80)):
        pieces = [piece for doc in docs for piece in chunk(doc, size, overlap)]
        unique = list(dict.fromkeys(p.text for p in pieces if p.text not in embedded))
        embedded.update(zip(unique, embed(unique, settings), strict=True))
        matrix = np.asarray([embedded[p.text] for p in pieces])
        matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)
        refs = [{"chunk_id": p.id, **p.metadata()} for p in pieces]
        rows = []
        for row in questions:
            question = row["question"]
            vector = np.asarray(vectors[question])
            scores = matrix @ vector / np.linalg.norm(vector)
            ranking = scores.argsort()[::-1]
            selected = [i for i in ranking if eligible(refs[i], question)][:5]
            hits = [{**refs[i], "score": float(scores[i])} for i in selected]
            unfiltered = [{**refs[i], "score": float(scores[i])} for i in ranking[:5]]
            rows.append({"id": row["id"], "type": row["type"], "hits": hits,
                         "unfiltered": unfiltered,
                         **{f"recall@{k}": recall_at_k(row.get("relevant", []), hits, k)
                            for k in (1, 3, 5)}})
        result = {
            "size": size, "overlap": overlap, "chunks": len(pieces),
            "amplification": sum(len(p.text.split()) for p in pieces) / source_words,
            **{f"recall@{k}": average([row[f"recall@{k}"] for row in rows]) for k in (1, 3, 5)},
            "rows": rows,
        }
        report["settings"].append(result)
        print({k: v for k, v in result.items() if k != "rows"}, flush=True)
    report["pairs"] = [
        {"equivalent": equivalent, "a": a, "b": b, "similarity": cosine(vectors[a], vectors[b]),
         "same_scope": scope(a) == scope(b)}
        for equivalent, a, b in PAIRS
    ]
    report["thresholds"] = [
        {"threshold": threshold,
         "true_hits": sum(p["equivalent"] and p["same_scope"] and p["similarity"] >= threshold
                          for p in report["pairs"]),
         "false_hits": sum(not p["equivalent"] and p["same_scope"] and p["similarity"] >= threshold
                           for p in report["pairs"])}
        for threshold in (0.85, 0.90, 0.96)
    ]
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=Path(".local-run/extracted.json"))
    parser.add_argument("--golden", type=Path, default=Path("eval/golden.yaml"))
    parser.add_argument("--out", type=Path, default=Path(".local-run/tuning.json"))
    parser.add_argument("--extract-only", action="store_true")
    args = parser.parse_args()
    docs = documents(args.snapshot)
    if not args.extract_only:
        run(docs, args.golden, args.out)
