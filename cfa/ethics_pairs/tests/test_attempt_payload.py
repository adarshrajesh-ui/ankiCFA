# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""INC5 — the minimal-pair FRONT card emits a structured attempt-detail payload.

On a completed attempt the pairs card persists a rich grade payload to
``localStorage["cfaEthics:pending"]`` (and sends it via the pycmd relay the back consumes) so W5 can
store it in ``card.custom_data`` (which syncs). This test drives the REAL front template through
headless Chrome (the same tap/judge/Check flow a learner performs) and asserts the emitted payload
matches the documented shape in proof/friday/ethics/HANDOFF.md — verdict per case, highlight span
token-index ranges, per-span tiers, overall grade, source, standard, item_id.

No ``anki`` dependency. Skipped when neither Chrome nor Chromium is available (e.g. minimal CI).
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PKG))
sys.path.insert(0, PKG)

from ethics_scoring import find_gold_spans  # noqa: E402

RENDER = os.path.join(REPO, "tools", "cfa", "render_pairs_attempt.py")

_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def _find_chrome() -> str | None:
    for c in _CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


CHROME = _find_chrome()
PYBIN = sys.executable

pytestmark = pytest.mark.skipif(CHROME is None, reason="no Chrome/Chromium for headless drive")


def _drive_and_extract(pair_id: str, mode: str) -> dict:
    """Render the pairs card, drive a full attempt headlessly, return the emitted payload dict."""
    with tempfile.TemporaryDirectory() as d:
        page = os.path.join(d, "card.html")
        subprocess.run(
            [PYBIN, RENDER, "--pair", pair_id, "--mode", mode, "--out", page],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        )
        proc = subprocess.run(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--virtual-time-budget=3000",
                "--dump-dom",
                f"file://{page}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        dom = proc.stdout
    m = re.search(r'<pre id="cfa-emitted-payload"[^>]*>(.*?)</pre>', dom, re.S)
    assert m, "card did not emit a cfa-emitted-payload element (attempt not completed?)"
    raw = html.unescape(m.group(1)).strip()
    assert raw, "emitted payload is empty (localStorage relay not set)"
    return json.loads(raw)


def test_front_emits_full_payload_shape_on_perfect_attempt():
    p = _drive_and_extract("SMD-01", "perfect")

    # Top-level contract (documented in HANDOFF.md -> W5).
    required = {
        "pairId",
        "itemId",
        "cluster",
        "completed",
        "correct",
        "standard",
        "source",
        "verdicts",
        "decisiveCase",
        "highlight",
        "found",
        "near",
        "total",
        "selectionIndices",
        "spans",
    }
    assert required.issubset(p), f"missing keys: {required - set(p)}"

    assert p["pairId"] == "SMD-01" and p["itemId"] == "SMD-01"
    assert p["completed"] is True and p["correct"] is True
    assert p["standard"] == "II(A) Material Nonpublic Information"
    assert p["source"] == "fallback"  # deterministic reveal (no AI bridge in this render)
    assert p["decisiveCase"] in ("A", "B")

    # Per-case verdicts.
    for c in ("A", "B"):
        v = p["verdicts"][c]
        assert set(v) == {"judged", "answer", "ok"}
        assert v["ok"] is (v["judged"] == v["answer"])

    # Multi-span highlight detail: a perfect attempt covers every gold span.
    assert p["highlight"] == "correct"
    assert p["found"] == p["total"] and p["total"] >= 2 and p["near"] == 0
    assert isinstance(p["selectionIndices"], list) and p["selectionIndices"]

    # Per-span token-index ranges + tiers.
    assert len(p["spans"]) == p["total"]
    for sp in p["spans"]:
        assert set(sp) >= {"phrase", "rationale", "tier", "matched", "lo", "hi"}
        assert sp["tier"] in ("full", "near", "none")
        assert sp["matched"] is (sp["tier"] != "none")
        assert isinstance(sp["lo"], int) and isinstance(sp["hi"], int) and sp["lo"] <= sp["hi"]
        assert sp["tier"] == "full"  # perfect attempt

    # The emitted per-span ranges match the deterministic gold-span token runs for this pair.
    import json as _json

    pairs = {
        r["pair_id"]: r
        for r in (
            _json.loads(line)
            for line in open(os.path.join(PKG, "pairs.jsonl"), encoding="utf-8")
            if line.strip()
        )
    }
    src = pairs["SMD-01"]
    vign = src["vignette_a"] if p["decisiveCase"] == "A" else src["vignette_b"]
    runs = find_gold_spans(vign, [g["phrase"] for g in src["gold_spans"]])
    emitted = [[sp["lo"], sp["hi"]] for sp in p["spans"]]
    assert emitted == [[r[0], r[-1]] for r in runs]


def test_front_emits_partial_grade_on_partial_attempt():
    p = _drive_and_extract("SMD-03", "partial")
    # Partial attempt highlights only the first of several spans -> partial credit, not fully correct.
    assert p["completed"] is True and p["correct"] is False
    assert p["highlight"] == "partial"
    assert p["found"] < p["total"]
    matched = [sp for sp in p["spans"] if sp["matched"]]
    assert 0 < len(matched) < p["total"]
