"""Small Ollama-compatible embedding double for the Kubernetes fixture job."""
from __future__ import annotations

import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "fixture-hash-v1"
STOP = set("a an and are as at be by can do for from how i if in is it much my now of on or "
           "the their to was what when where who will with you your apply".split())


def vector(text: str) -> list[float]:
    values = [0.0] * 1024
    for token in re.findall(r"[a-z]+|\d+", text.lower()):
        token = token.removesuffix("s") if len(token) > 4 else token
        if token in STOP:
            continue
        bucket = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=4).digest(), "big")
        values[bucket % len(values)] += 1.0
    return values


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()

    def do_POST(self) -> None:
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path != "/api/embed" or data.get("model") != MODEL:
            self.send_error(400)
            return
        body = json.dumps({"model": MODEL, "embeddings": [vector(t) for t in data["input"]]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 11434), Handler).serve_forever()
