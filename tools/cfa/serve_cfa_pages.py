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
import random
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
from PyQt6.QtWidgets import QApplication  # noqa: E402

import aqt  # noqa: E402
from anki import cfa  # noqa: E402
from anki.cards import CardId  # noqa: E402
from anki.collection import Collection  # noqa: E402
from anki.decks import DeckId  # noqa: E402
from aqt import mediasrv  # noqa: E402

DAY = 86_400

# (tag, n_cards, mastery, reviews_each, n_first_correct, exam_weight)
# `mastery` picks a base FSRS stability + a base days-since-review; both are
# jittered PER CARD (deterministically) so today's per-topic recall spreads into
# a realistic gradient (strong topics ~high R, weak topics lower R) instead of
# every card pinning at 100%. ~81% first-exposure accuracy across 94 cards keeps
# the hero a confident "likely pass".
TOPICS: list[tuple[str, int, str, int, int, float]] = [
    ("los::ethics", 14, "strong", 6, 12, 0.12),
    ("los::fra", 16, "strong", 6, 13, 0.15),
    ("los::equity", 14, "medium", 6, 11, 0.13),
    ("los::portmgmt", 12, "medium", 6, 10, 0.11),
    ("los::corp", 10, "medium", 5, 9, 0.11),
    ("los::econ", 10, "weak", 5, 6, 0.09),
    ("los::quant", 10, "weak", 6, 6, 0.09),
    ("los::altinv", 8, "weak", 5, 5, 0.10),
]

# base_stability_days, base_days_since_last_review.
# FSRS "recall now" ~ f(days_since_review / stability). Ageing the last-review
# time per mastery band is what actually spreads the readiness column: strong
# cards were seen recently vs a big stability (R~0.99); weak cards were seen long
# ago vs a small stability (R dips into the 0.60s). The same ageing, extended to
# the exam date, gives the deadline view its at-risk (warn) gradient.
MASTERY: dict[str, tuple[float, float]] = {
    "strong": (300.0, 9.0),
    "medium": (85.0, 34.0),
    "weak": (26.0, 78.0),
}


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
    stabilities: list[float],
    elapsed_days: list[int],
    reviews_each: int,
    first_ease: list[int],
    now: int,
) -> list[CardId]:
    """Seed ``n_cards`` review cards under ``topic``, each with its own FSRS
    memory state (per-card ``stabilities`` + per-card ``elapsed_days`` since the
    last review) plus ``reviews_each`` graded reviews.

    Adapted from the authoritative ``_seed_topic`` in
    ``pylib/tests/test_cfa_scores.py`` (same card/revlog shape the score maths is
    unit-tested against); the only change is per-card stability + last-review age
    so FSRS recall spreads into a realistic gradient instead of a flat 100%. The
    interval mirrors the elapsed age so the card reads as legitimately due."""
    cids = [
        _add_card(col, deck_id, notetype, f"{topic}-{i}", [f"{topic}::r1"])
        for i in range(n_cards)
    ]
    col.sched.set_due_date(cids, "0")  # -> review cards, due today
    updates = [
        (
            json.dumps(
                {"s": stabilities[i], "d": 5.0, "lrt": now - elapsed_days[i] * DAY}
            ),
            elapsed_days[i],
            c,
        )
        for i, c in enumerate(cids)
    ]
    col.db.executemany("update cards set data=?, ivl=? where id=?", updates)

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
    full of real, VARIED numbers and the hero lands in the 'likely pass' state.

    Per-card stability + interval are jittered with a fixed-seed RNG, so the run
    is reproducible yet the per-topic recall ranges and the weakest-first
    deadline ranking show a genuine gradient (some at-risk/warn rows included)."""
    now = int(time.time())
    rng = random.Random(20260703)
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA Level II")
    weights: dict[str, float] = {}
    for tag, n_cards, mastery, reviews_each, n_correct, weight in TOPICS:
        base_stab, base_elapsed = MASTERY[mastery]
        stabilities = [base_stab * (0.7 + 0.6 * rng.random()) for _ in range(n_cards)]
        elapsed_days = [
            max(1, round(base_elapsed * (0.6 + 0.8 * rng.random())))
            for _ in range(n_cards)
        ]
        first_ease = [3] * n_correct + [1] * (n_cards - n_correct)
        _seed_topic(
            col,
            deck,
            nt,
            tag,
            n_cards,
            stabilities=stabilities,
            elapsed_days=elapsed_days,
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
