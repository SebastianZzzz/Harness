from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from aegis_harness.config import Settings
from aegis_harness.live_state_machine import AegisHarnessLiveBackend


ROOT = Path(__file__).resolve().parents[1]
backend = AegisHarnessLiveBackend(Settings.from_env(ROOT))


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self._send_empty(204)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(
                {
                    "ok": True,
                    "model": backend.ai.model_name,
                    "provider": backend.ai.provider_label,
                }
            )
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/tasks":
                payload = self._read_json()
                task = backend.start(str(payload.get("request", "")))
                self._send_json(task.to_dict())
                return

            if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/approve"):
                task_id = int(parsed.path.split("/")[3])
                payload = self._read_json()
                task = backend.approve(task_id, payload.get("prompt"))
                self._send_json(task.to_dict())
                return

            if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/reject"):
                task_id = int(parsed.path.split("/")[3])
                task = backend.reject(task_id)
                self._send_json(task.to_dict())
                return

            self._send_json({"error": "Not found"}, status=404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self._headers()
        self.end_headers()

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _headers(self) -> None:
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: object) -> None:
        print(f"[aegis-api] {self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print(f"AegisHarness backend listening on http://127.0.0.1:8000 using {backend.ai.model_name}")
    server.serve_forever()


if __name__ == "__main__":
    main()
