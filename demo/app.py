"""Laptop demo: type a review, watch the device model answer, decide whether to send it to the hub, and see
the simulated energy the ESP32-S3 would spend. Standard library server; models in demo/engine.py.

    .venv/bin/python -I demo/app.py          # then open http://localhost:8770
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I leaves the script dir off sys.path

from engine import Engine  # noqa: E402

PORT = 8770
PAGE = Path(__file__).resolve().parent / "index.html"
MAX_CHARS = 20_000

print("loading models (device, router, RoBERTa-base hub)...", flush=True)
ENGINE = Engine()
LOCK = threading.Lock()  # one request at a time on the GPU
INFO = json.dumps(ENGINE.info()).encode()
print(f"ready in {ENGINE.load_seconds:.1f}s: open http://localhost:{PORT}", flush=True)


def options(body):
    policy = body.get("policy", "confidence")
    rate = float(body.get("rate", 0.16))
    if policy not in Engine.POLICIES or not 0 <= rate <= 1:
        raise ValueError("policy must be confidence or learned, rate between 0 and 1")
    return policy, rate


class Handler(BaseHTTPRequestHandler):
    def send(self, code, data, kind="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/info":
            self.send(200, INFO)
        else:
            self.send(404, b'{"error":"not found"}')

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            policy, rate = options(body)
            with LOCK:
                if self.path == "/api/classify":
                    text = str(body.get("text", ""))[:MAX_CHARS]
                    if not text.strip():
                        raise ValueError("type a review first")
                    result = ENGINE.classify(text, policy, rate)
                elif self.path == "/api/batch":
                    result = ENGINE.batch(int(body.get("n", 100)), policy, rate, int(body.get("seed", 0)))
                else:
                    return self.send(404, b'{"error":"not found"}')
            self.send(200, json.dumps(result).encode())
        except (ValueError, json.JSONDecodeError) as e:
            self.send(400, json.dumps({"error": str(e)}).encode())

    def log_message(self, *args):  # keep the terminal quiet
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
