#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA AI proxy — server-side AI for mobile (the key never leaves the server).

AnkiDroid cannot safely hold the OpenAI key (a device has no ``.env``). So the
phone POSTs to this small proxy running alongside the self-hosted sync server;
the proxy holds the key (via :mod:`cfa.ai.llm_client`, which reads ``.env``) and
returns the AI draft / grade WITH provenance. A shared bearer token — NOT the
OpenAI key — gates access.

Endpoints (Authorization: Bearer <token>; JSON bodies):
  POST /cfa/tabfill  {front, notetype?}            -> {ok, text, source, model, error}
  POST /cfa/grade    {passage, answerVerdict, ...}  -> ai_grading.grade_semantic result
  GET  /cfa/health                                  -> {ok, keyPresent, model}

The OpenAI key is NEVER returned or logged. With no key (or on any failure) every
endpoint returns a deterministic ``source == "fallback"`` response, so mobile
stays usable — the SAME AI-off contract as the desktop.

Run:  just cfa-ai-proxy      # host 0.0.0.0 port 27702; emulator -> 10.0.2.2:27702
Token: set CFA_AI_PROXY_TOKEN (default "cfa-ai-proxy" for dev).
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional

# Put the repo root (+ ethics_pairs) on sys.path so cfa.ai.llm_client and the
# pure ai_grading module import regardless of CWD.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, "cfa", "ethics_pairs")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cfa.ai import llm_client  # noqa: E402

DEFAULT_TOKEN = "cfa-ai-proxy"
DEFAULT_PORT = 27702

def _token() -> str:
    return os.environ.get("CFA_AI_PROXY_TOKEN", DEFAULT_TOKEN)


def fill(
    front: str = "",
    back: str = "",
    notetype: str = "",
    *,
    complete_fn=None,
) -> dict[str, Any]:
    """Bidirectional tab-fill: generate whichever side is empty from the filled
    one (front->back or back->front). Returns provenance; never raises. ``source``
    is "ai" on success, "fallback" on AI-off / any failure / nothing-to-fill."""
    from cfa.ai import tabfill as tabfill_lib

    target = tabfill_lib.infer_target(front, back)
    if target is None:
        return {"ok": False, "text": "", "target": None, "source": "fallback",
                "model": None, "error": "nothing_to_fill"}
    source_text = front if target == "back" else back
    system, user = tabfill_lib.build_messages(source_text, target, notetype)
    if complete_fn is None:
        complete_fn = llm_client.complete
    res = complete_fn(
        system, user, max_tokens=400, temperature=0.2,
        purpose=f"tabfill_{target}_mobile",
    )
    if not isinstance(res, dict) or not res.get("ok"):
        return {"ok": False, "text": "", "target": target, "source": "fallback",
                "model": (res or {}).get("model"),
                "error": (res or {}).get("error", "ai_unavailable")}
    text = (res.get("text") or "").strip()
    if not text:
        return {"ok": False, "text": "", "target": target, "source": "fallback",
                "model": res.get("model"), "error": "empty_completion"}
    return {"ok": True, "text": text, "target": target, "source": "ai",
            "model": res.get("model"), "error": None}


def grade(payload: dict[str, Any], *, complete_fn=None) -> dict[str, Any]:
    """Semantic ethics grade via the shared pure grader (falls back on failure)."""
    from ai_grading import grade_semantic

    return grade_semantic(
        str(payload.get("passage", "")),
        str(payload.get("answerVerdict", "")),
        str(payload.get("judgedVerdict", "")),
        payload.get("goldSpans") or [],
        [str(p) for p in (payload.get("learnerSpans") or [])],
        item_id=str(payload.get("itemId", "")),
        standard=str(payload.get("standard", "")),
        complete_fn=complete_fn,
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "cfa-ai-proxy/1.0"

    def _authed(self) -> bool:
        return self.headers.get("Authorization") == f"Bearer {_token()}"

    def _send(self, code: int, obj: dict[str, Any]) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Never log request lines/bodies/headers — key/PII hygiene.
    def log_message(self, *args: Any) -> None:  # noqa: D401
        return

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/cfa/health":
            if not self._authed():
                return self._send(401, {"error": "unauthorized"})
            return self._send(200, {
                "ok": True,
                "keyPresent": llm_client.key_present(),
                "model": llm_client._model(),
            })
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if not self._authed():
            return self._send(401, {"error": "unauthorized"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        route = self.path.rstrip("/")
        try:
            if route == "/cfa/tabfill":
                return self._send(200, fill(
                    str(payload.get("front", "")),
                    str(payload.get("back", "")),
                    str(payload.get("notetype", ""))))
            if route == "/cfa/grade":
                return self._send(200, grade(payload))
        except Exception as exc:  # pragma: no cover - endpoints are no-raise
            return self._send(200, {"ok": False, "source": "fallback",
                                    "error": f"proxy_error:{type(exc).__name__}"})
        self._send(404, {"error": "not_found"})


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="CFA AI proxy for mobile")
    ap.add_argument("--host", default=os.environ.get("CFA_AI_PROXY_HOST", "0.0.0.0"))
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("CFA_AI_PROXY_PORT", str(DEFAULT_PORT))))
    args = ap.parse_args(argv)

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    # keyPresent is a bool; the key itself is never printed.
    print(
        f"CFA_AI_PROXY_READY host={args.host} port={args.port} "
        f"keyPresent={llm_client.key_present()}",
        flush=True,
    )
    print(
        f"  emulator -> http://10.0.2.2:{args.port}/  ·  "
        f"token via CFA_AI_PROXY_TOKEN (default {DEFAULT_TOKEN!r})",
        flush=True,
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
