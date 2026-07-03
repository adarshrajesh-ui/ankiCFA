# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Serve the REAL live CFA SvelteKit pages against a richly-seeded collection.

This stands up the ACTUAL ``aqt.mediasrv`` Flask/waitress server — the same one
the desktop app runs — bound to ``ANKI_API_PORT`` (default 40000), so the live
pages can be screenshotted exactly as the app serves them:

* ``http://127.0.0.1:40000/cfa-readiness/<deckId>``
* ``http://127.0.0.1:40000/cfa-deadline/<deckId>``

Method / honesty note
---------------------
Nothing about the DATA path is mocked. The pages are the real built SvelteKit
bundle (``out/qt/_aqt/data/web/sveltekit``); the payloads come from the real
``mediasrv._cfa_exam_readiness_payload`` / ``_cfa_deadline_payload`` handlers,
which read ``aqt.mw.col``. The ONLY stand-in is ``aqt.mw`` itself: instead of a
full ``AnkiQt`` main window (which needs a real GUI event loop / profile
manager), we install a tiny object whose only job is to expose ``.col`` — a
real, richly-seeded :class:`anki.collection.Collection`. This mirrors how the
app boots mediasrv (``AnkiQt.setupMediaServer`` -> ``MediaServer(self)``), minus
the windowing. An offscreen ``QApplication`` is created so the Qt-importing
mediasrv module loads cleanly.

The seed reuses the authoritative ``_seed_topic`` pattern from
``pylib/tests/test_cfa_scores.py`` (the same FSRS-memory + first-exposure mix
that ``tools/cfa/render_f5_proof.py`` used to render the old dialogs), scaled up
to all eight canonical CFA Level II topics so the readiness hero lands in the
"likely pass" state and every table is full of real numbers.

Usage:
    QT_QPA_PLATFORM=offscreen ANKI_API_PORT=40000 \
        PYTHONPATH="out/pylib:pylib:qt:out/qt" \
        out/pyenv/bin/python tools/cfa/serve_cfa_pages.py
"""

from __future__ import annotations

import json
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ANKI_API_PORT", "40000")
# The mediasrv POST gate (`_check_dynamic_request_permissions`) only lets a page
# reach the CFA RPCs if it carries the injected API key OR ANKI_API_HOST is
# "0.0.0.0" (Anki's own "trust local API" switch). An external headless Chrome
# has no injected key, so we flip that switch — the SAME code path the app uses,
# yielding byte-identical payloads. It also relaxes the localhost Host/Origin
# check for the capture. (Short-lived, dev-only; the server is killed after.)
os.environ.setdefault("ANKI_API_HOST", "0.0.0.0")

# Import aqt (which pulls in QtWebEngineWidgets) BEFORE any QApplication instance
# exists, else Qt raises "QtWebEngineWidgets must be imported ... before a
# QCoreApplication instance is created". This mirrors tools/cfa/render_f5_proof.py.
import aqt  # noqa: E402
from aqt import mediasrv  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from anki import cfa  # noqa: E402
from anki.cards import CardId  # noqa: E402
from anki.collection import Collection  # noqa: E402
from anki.decks import DeckId  # noqa: E402

DAY = 86_400

# (tag, n_cards, stability, reviews_each, n_first_correct, exam_weight)
# Stability is deliberately spread so per-topic FSRS recall — and the
# predicted-recall-at-exam ranking on the deadline page — vary realistically.
# ~81% first-exposure accuracy across 94 cards => a confident "likely pass".
TOPICS: list[tuple[str, int, float, int, int, float]] = [
    ("los::ethics", 14, 400.0, 6, 12, 0.12),
    ("los::fra", 16, 300.0, 6, 13, 0.15),
    ("los::equity", 14, 90.0, 6, 11, 0.13),
    ("los::portmgmt", 12, 150.0, 6, 10, 0.11),
    ("los::corp", 10, 220.0, 5, 9, 0.11),
    ("los::econ", 10, 120.0, 5, 8, 0.09),
    ("los::quant", 10, 60.0, 6, 7, 0.09),
    ("los::altinv", 8, 45.0, 5, 6, 0.10),
]


def _add_card(
    col: Collection, deck_id: DeckId, notetype, front: str, tags: list[str]
) -> CardId:
    note = col.new_note(notetype)
    note["Front"] = front
    note["Back"] = "answer"
    note.tags = tags
    col.add_note(note, deck_id)
    return col.find_cards(f"nid:{note.id}")[0]


def _seed_topic(
    col: Collection,
    deck_id: DeckId,
    notetype,
    topic: str,
    n_cards: int,
    *,
    stability: float,
    reviews_each: int,
    first_ease: list[int],
    now: int,
) -> list[CardId]:
    """Seed ``n_cards`` review cards under ``topic`` with an FSRS memory state
    (fixed ``stability``) and ``reviews_each`` graded reviews each.

    Copied verbatim from ``pylib/tests/test_cfa_scores.py`` so the live pages are
    fed the same shape the score maths is unit-tested against."""
    cids = [
        _add_card(col, deck_id, notetype, f"{topic}-{i}", [f"{topic}::r1"])
        for i in range(n_cards)
    ]
    col.sched.set_due_date(cids, "0")  # -> review cards, due today
    data = json.dumps({"s": stability, "d": 5.0, "lrt": now - DAY})
    col.db.executemany(
        "update cards set data=?, ivl=? where id=?", [(data, 20, c) for c in cids]
    )

    base = (col.db.scalar("select coalesce(max(id), 0) from revlog") or 0) + 1
    rows = []
    n = 0
    for idx, c in enumerate(cids):
        for j in range(reviews_each):
            ease = first_ease[idx] if j == 0 else 3
            # id, cid, usn, ease, ivl, lastIvl, factor, time, type(review)
            rows.append((base + n, c, -1, ease, 10, 5, 2500, 1000, 1))
            n += 1
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return cids


def seed_rich(col: Collection) -> DeckId:
    """Seed all eight canonical topics so every readiness/deadline surface is
    full of real numbers and the hero lands in the 'likely pass' state."""
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA Level II")
    weights: dict[str, float] = {}
    for tag, n_cards, stability, reviews_each, n_correct, weight in TOPICS:
        first_ease = [3] * n_correct + [1] * (n_cards - n_correct)
        _seed_topic(
            col,
            deck,
            nt,
            tag,
            n_cards,
            stability=stability,
            reviews_each=reviews_each,
            first_ease=first_ease,
            now=now,
        )
        weights[tag] = weight
    cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights=weights)
    return deck


class _NoopTaskman:
    """Defensive no-op so any stray permission-warning path can't AttributeError."""

    def run_on_main(self, func) -> None:  # pragma: no cover - defensive only
        pass

    def run_in_background(self, *a, **k) -> None:  # pragma: no cover
        pass


class _MW:
    """Minimal ``aqt.mw`` stand-in: the mediasrv CFA handlers only read ``.col``.

    ``taskman`` is a defensive no-op; with ANKI_API_HOST=0.0.0.0 the permission
    gate grants access before it is ever consulted, but stubbing it keeps any
    unexpected warning path from crashing the request thread."""

    def __init__(self, col: Collection) -> None:
        self.col = col
        self.taskman = _NoopTaskman()

    def reset(self) -> None:  # pragma: no cover - never called in this flow
        pass


def main() -> int:
    app = QApplication.instance() or QApplication(["serve"])
    assert app is not None

    base = os.environ.get("CFA_SERVE_COL") or "/tmp/cfa-serve/collection.anki2"
    os.makedirs(os.path.dirname(base), exist_ok=True)
    for p in (base, base + "-wal", base + "-shm"):
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass

    col = Collection(base)
    deck = seed_rich(col)
    col.decks.select(deck)

    mw = _MW(col)
    aqt.mw = mw  # type: ignore[assignment]

    # Sanity: compute the real payloads once and print a compact summary so the
    # caller can confirm the data is genuine (not a mock) before screenshotting.
    readiness = mediasrv._cfa_exam_readiness_payload(col, int(deck))
    deadline = mediasrv._cfa_deadline_payload(col, int(deck))
    hero = readiness.get("heroBayesian") or readiness.get("heroAbstain")
    print("=== CFA payload sanity ===", flush=True)
    print(
        "readiness: heroMode=%s call=%s graded=%s firstExp=%s topics=%s/%s"
        % (
            readiness["heroMode"],
            (hero or {}).get("call"),
            readiness["caption"]["gradedReviews"],
            readiness["caption"]["firstExposures"],
            readiness["caption"]["topicsCovered"],
            readiness["caption"]["topicsTotal"],
        ),
        flush=True,
    )
    print(
        "deadline: cards=%s source=%s mode=%s examDate=%s"
        % (
            deadline["cardCount"],
            deadline["dataSource"],
            deadline["headerMode"],
            deadline["examDate"],
        ),
        flush=True,
    )

    server = mediasrv.MediaServer(mw)  # type: ignore[arg-type]
    server.start()
    port = server.getPort()
    print(
        f"CFA_SERVE_READY port={port} deck_id={int(deck)} "
        f"readiness_url=http://127.0.0.1:{port}/cfa-readiness/{int(deck)} "
        f"deadline_url=http://127.0.0.1:{port}/cfa-deadline/{int(deck)}",
        flush=True,
    )

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        col.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
