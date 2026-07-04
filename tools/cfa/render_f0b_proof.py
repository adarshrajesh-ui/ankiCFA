# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render REAL proof of the F0b desktop "Peak-on-Exam-Day" (Deadline) surface.

The DeadlineDialog is now a thin host for the shared ``ts/lib/cfa`` SvelteKit
page (it no longer owns a ``QDateEdit`` body); it loads ``cfa-deadline/<deckId>``
from mediasrv. So this script stands up the SAME real ``aqt.mediasrv`` server the
desktop app runs — exactly as ``tools/cfa/serve_cfa_pages.py`` does — and
screenshots the live page with headless Chrome (a reliable capture; an offscreen
QWebEngine grab cannot composite in this environment).

Nothing about the DATA path is mocked: the payload comes from the real
``mediasrv._cfa_deadline_payload`` handler reading ``aqt.mw.col``; the only
stand-in is ``aqt.mw`` (a tiny object exposing ``.col`` + ``.taskman``), mirroring
how the app boots mediasrv minus the windowing.

Renders two states so the surface is visibly functional:

* ``f0b-deadline-default.png`` — the seeded ``CFA::Ethics Pairs`` deck (all new
  cards) with no persisted exam date: the page self-heals to the canonical
  default exam day and ranks the new cards weakest-first.
* ``f0b-deadline-picked.png``  — after persisting a different exam date via the
  real ``anki.cfa.set_exam_config`` API and reloading the page.

Usage: QT_QPA_PLATFORM=offscreen python tools/cfa/render_f0b_proof.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Let external headless Chrome reach the CFA RPCs without an injected API key
# (the same "trust local API" switch tools/cfa/serve_cfa_pages.py uses).
os.environ.setdefault("ANKI_API_HOST", "0.0.0.0")

# Import aqt (which pulls in QtWebEngineWidgets) BEFORE any QApplication instance
# exists, else Qt raises the "must be imported before a QCoreApplication" error.
from PyQt6.QtWidgets import QApplication  # noqa: E402

import aqt  # noqa: E402
from anki import cfa as anki_cfa  # noqa: E402
from anki.collection import Collection  # noqa: E402
from aqt import mediasrv  # noqa: E402
from aqt.cfa_seed import ensure_ethics_deck  # noqa: E402

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "proof",
    "gnhf2",
)

# Candidate headless-Chrome binaries, in preference order (Chrome channel first,
# then the Playwright-bundled Chromium the repo already vendors under out/).
_CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
    shutil.which("chromium-browser") or "",
)


class _NoopTaskman:
    """No-op taskman so any stray permission-warning path can't AttributeError."""

    def run_on_main(self, func) -> None:  # pragma: no cover - defensive only
        pass

    def run_in_background(self, *a, **k) -> None:  # pragma: no cover
        pass


class _MW:
    """Minimal ``aqt.mw`` stand-in — the mediasrv CFA handlers only read ``.col``.

    Mirrors ``tools/cfa/serve_cfa_pages.py``'s stand-in; ``taskman`` is defensive
    (with ANKI_API_HOST=0.0.0.0 the permission gate grants access before it is
    consulted)."""

    def __init__(self, col: Collection) -> None:
        self.col = col
        self.taskman = _NoopTaskman()

    def reset(self) -> None:  # pragma: no cover - never called in this flow
        pass


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def _find_chrome() -> str:
    for cand in _CHROME_CANDIDATES:
        if cand and os.path.exists(cand):
            return cand
    # Playwright's bundled Chromium (the repo vendors it under out/node_modules).
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for base in (
        os.path.expanduser("~/Library/Caches/ms-playwright"),
        os.path.join(repo, "out", "node_modules", "playwright-core", ".local-browsers"),
    ):
        if os.path.isdir(base):
            for root, _dirs, files in os.walk(base):
                for f in files:
                    if f in ("Chromium", "Google Chrome for Testing", "chrome"):
                        cand = os.path.join(root, f)
                        if os.access(cand, os.X_OK):
                            return cand
    raise RuntimeError(
        "no headless Chrome/Chromium found; install Chrome or run just setup"
    )


def _screenshot(chrome: str, url: str, name: str) -> str:
    path = os.path.join(OUT_DIR, name)
    with tempfile.TemporaryDirectory() as profile:
        subprocess.check_call(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--user-data-dir={profile}",
                "--window-size=560,700",
                "--virtual-time-budget=6000",
                f"--screenshot={path}",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if not os.path.exists(path):
        raise RuntimeError(f"chrome did not write {path}")
    return path


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    app = QApplication.instance() or QApplication(["render"])
    assert app is not None
    chrome = _find_chrome()

    col = _empty_col()
    mw = _MW(col)
    aqt.mw = mw  # type: ignore[assignment]

    server = mediasrv.MediaServer(mw)  # type: ignore[arg-type]
    server.start()
    port = server.getPort()

    try:
        # Preload the ethics deck so the collection is realistic (all new cards)
        # and make it the current deck the dialog scopes its page to.
        ensure_ethics_deck(col)
        ethics_did = col.decks.id_for_name("CFA::Ethics Pairs")
        if ethics_did is not None:
            col.decks.select(ethics_did)
        deck_id = int(col.decks.get_current_id())
        url = f"http://127.0.0.1:{port}/cfa-deadline/{deck_id}"

        # State 1: no persisted exam date -> the page self-heals to the default.
        payload = mediasrv._cfa_deadline_payload(col, deck_id)
        p1 = _screenshot(chrome, url, "f0b-deadline-default.png")
        print(
            f"wrote {p1} (default examDate={payload['examDate']} "
            f"cards={payload['cardCount']} mode={payload['headerMode']})"
        )

        # State 2: persist a different exam date via the real API, then reload.
        anki_cfa.set_exam_config(col, exam_date="2027-05-15", topic_weights={})
        # Small settle so the reloaded page reflects the new persisted date.
        time.sleep(0.3)
        payload = mediasrv._cfa_deadline_payload(col, deck_id)
        p2 = _screenshot(chrome, url, "f0b-deadline-picked.png")
        stored = anki_cfa.get_exam_config(col) or {}
        print(f"wrote {p2} (persisted exam_date={stored.get('exam_date')})")
    finally:
        col.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
