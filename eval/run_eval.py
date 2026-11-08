#!/usr/bin/env python3
"""Score a running RAHBAR against a golden set, and gate CI on the result (section 5).

    python eval/run_eval.py --api http://<ingress>                 # your corpus
    python eval/run_eval.py --api ... --golden eval/fixtures/golden.fixture.yaml
    python eval/run_eval.py --api ... --update-baseline            # after a deliberate improvement

Exit code 0 when every gate passes, 1 when any fails. CI relies on that exit code.

Report retrieval, provenance and abstention from a live endpoint.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from statistics import mean
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent

# The gate from section 5.4. Change these only with a reason written in docs/PIPELINE.md.
MAX_RECALL5_DROP = 0.05        # recall@5 may fall at most 5 points below the baseline
MIN_CITATION_VALIDITY = 0.95   # at least 95% of citations must match retrieved passages
REQUIRED_ABSTENTION = 1.0      # every must-abstain question must be declined


def load_golden(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = data.get("questions") or []
    if not questions:
        sys.exit(f"no questions in {path}")
    return questions


def ask(client: httpx.Client, api: str, question: str) -> dict:
    """POST one question and return the AskResponse as a dict (see api/app/schemas.py)."""
    response = client.post(f"{api.rstrip('/')}/api/ask", json={"question": question})
    response.raise_for_status()
    return response.json()


def recall_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    if not relevant:
        return None
    targets = {(r.get("chunk_id"), r.get("source"), r.get("section")) for r in relevant}
    found = sum(
        any(hit.get("chunk_id") == key if key else
            (hit.get("source"), hit.get("section")) == (source, section)
            for hit in retrieved[:k])
        for key, source, section in targets
    )
    return found / len(targets)


def citation_key(item: dict) -> tuple:
    return item["source"], item["section"], item.get("page")


def citation_validity(response: dict) -> float | None:
    citations = response["citations"]
    if not citations:
        return 0.0 if response["answered_from_context"] else None
    retrieved = {citation_key(p) for p in response["retrieved"]}
    return sum(citation_key(c) in retrieved for c in citations) / len(citations)


def average(values: list[float | None]) -> float | None:
    scored = [value for value in values if value is not None]
    return mean(scored) if scored else None


def summarise(rows: list[dict]) -> dict:
    for row in rows:
        response = row["response"]
        for k in (3, 5):
            row[f"recall@{k}"] = recall_at_k(row["relevant"], response["retrieved"], k)
        row["citation_validity"] = citation_validity(response)
        row["expect_present"] = (row.get("expect", "").lower() in response["answer"].lower()
                                 if row.get("expect") else None)
    cited = [(row["citation_validity"], len(row["response"]["citations"]) or 1)
             for row in rows if row["citation_validity"] is not None]
    return {
        **{f"recall@{k}": average([row[f"recall@{k}"] for row in rows]) for k in (3, 5)},
        "by_type": {
            group: {f"recall@{k}": average([row[f"recall@{k}"] for row in rows
                                           if row["type"] == group]) for k in (3, 5)}
            for group in sorted({row["type"] for row in rows})
        },
        "citation_validity": (sum(value * count for value, count in cited)
                              / sum(count for _, count in cited)) if cited else None,
        "abstention_correctness": average([float(not row["response"]["answered_from_context"])
                                           for row in rows if row["must_abstain"]]),
        "answered_questions": sum(row["response"]["answered_from_context"] for row in rows),
        "rows": rows,
    }


def gate(results: dict, baseline: dict | None) -> list[str]:
    failures = []
    if results["recall@5"] is None:
        failures.append("Recall@5 has no scored questions")
    elif baseline and results["recall@5"] < baseline["recall@5"] - MAX_RECALL5_DROP - 1e-12:
        failures.append("Recall@5 dropped by more than 5 percentage points")
    if results["abstention_correctness"] != REQUIRED_ABSTENTION:
        failures.append("Abstention correctness must be 100%")
    if (results["citation_validity"] or 0) < MIN_CITATION_VALIDITY:
        failures.append("Citation validity must reach 95% with at least one evaluated answer")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAHBAR against a golden set.")
    parser.add_argument("--api", required=True, help="base URL, e.g. http://192.168.49.2")
    parser.add_argument("--host", help="Host header, when your Ingress rule names a host")
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--raw-out", type=Path, help="optional private transcript for manual review")
    parser.add_argument("--update-baseline", action="store_true",
                        help="write these results as the new baseline")
    args = parser.parse_args()

    questions = load_golden(args.golden)
    rows = []
    headers = {"Host": args.host} if args.host else {}
    with httpx.Client(timeout=180.0, headers=headers) as client:
        for q in questions:
            started = time.perf_counter()
            response = ask(client, args.api, q["question"])
            rows.append({
                "id": q["id"], "type": q.get("type", "ordinary"),
                "must_abstain": bool(q.get("must_abstain", False)),
                "relevant": q.get("relevant") or [],
                "expect": q.get("expect"),
                "response": response,
                "seconds": round(time.perf_counter() - started, 2),
            })
            print(f"  {q['id']:<5} {rows[-1]['seconds']:>6.2f}s  {q['question'][:60]}")

    results = summarise(rows)
    baseline = json.loads(args.baseline.read_text()) if args.baseline.exists() else None
    failures = gate(results, None if args.update_baseline else baseline)
    results["gate_failures"] = failures

    if args.raw_out:
        args.raw_out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    # Public artifacts retain provenance and outcome without copying source excerpts.
    results["rows"] = [
        {**row, "response": {k: v for k, v in row["response"].items() if k != "answer"}}
        for row in rows
    ]
    results["golden"] = str(args.golden)
    results["questions"] = len(rows)
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults written to {args.out}")
    if args.update_baseline and not failures:
        args.baseline.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"baseline updated: {args.baseline}")

    if failures:
        print("\nGATE FAILED")
        for message in failures:
            print(f"  - {message}")
        return 1
    print("\ngate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
