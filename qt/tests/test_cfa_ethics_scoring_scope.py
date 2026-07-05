# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""The CFA Home / Concept Map / Readiness scores must include the SIBLING
``CFA::Ethics Pairs`` deck.

The special ethics minimal-pairs cards live in ``CFA::Ethics Pairs`` — a sibling
of the ``CFA Level II`` deck, NOT a child of it — so the old
``_cfa_exam_readiness_payload(col, <CFA Level II deck id>)`` (which scopes to a
single deck subtree) silently EXCLUDED every ethics-pair review from the
desktop's headline scores, readiness verdict and concept-map fills. The AnkiDroid
client already scored the whole collection, so the same reviews produced
different numbers on desktop vs phone.

These tests prove the fix: the Home payload (and the readiness payload with
``deck_id == 0``) score the WHOLE collection, so ethics-pair reviews DO reach
them, while a real (non-zero) deck id still scopes to that one deck.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from anki.collection import Collection
from anki.decks import DeckId

import aqt.mediasrv as mediasrv

MAIN_DECK = "CFA Level II"
ETHICS_DECK = "CFA::Ethics Pairs"  # sibling of MAIN_DECK, NOT a child


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def _seed_reviewed(col: Collection, deck_id: DeckId, topic_tag: str, n: int, reviews: int) -> None:
    """Add ``n`` review cards under ``deck_id`` tagged ``topic_tag`` with FSRS
    memory state and ``reviews`` graded reviews apiece (direct DB writes)."""
    nt = col.models.by_name("Basic")
    now = int(time.time())
    cids = []
    for i in range(n):
        note = col.new_note(nt)
        note["Front"] = f"{topic_tag}-{i}"
        note["Back"] = "answer"
        note.tags = [f"{topic_tag}::r1"]
        col.add_note(note, deck_id)
        cids.append(col.find_cards(f"nid:{note.id}")[0])
    col.sched.set_due_date(cids, "0")
    data = json.dumps({"s": 60.0, "d": 5.0, "lrt": now - 86400})
    col.db.executemany("update cards set data=? where id=?", [(data, c) for c in cids])

    day_ms = 86_400 * 1000
    base_ms = now * 1000 - reviews * day_ms
    uid = col.db.scalar("select count(*) from revlog") or 0
    rows = []
    for c in cids:
        for j in range(reviews):
            rows.append((base_ms + j * day_ms + uid, c, -1, 3, 10, 5, 2500, 1000, 1))
            uid += 1
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )


def _ethics_topic(payload: dict) -> dict:
    from anki import cfa

    name = cfa.topic_display_name("los::ethics")
    return next(t for t in payload["topics"] if t["topic"] == name)


def test_whole_collection_payload_includes_ethics_sibling_deck() -> None:
    col = _empty_col()
    try:
        main = DeckId(col.decks.id(MAIN_DECK))
        ethics = DeckId(col.decks.id(ETHICS_DECK))
        # Reviews ONLY in the ethics-pairs sibling deck.
        _seed_reviewed(col, ethics, "los::ethics", n=3, reviews=5)

        whole = mediasrv._cfa_exam_readiness_payload(col, 0)
        scoped = mediasrv._cfa_exam_readiness_payload(col, int(main))

        # Whole-collection scoring sees the ethics-pair reviews...
        assert whole["caption"]["gradedReviews"] == 15
        assert _ethics_topic(whole)["gradedReviews"] == 15
        assert _ethics_topic(whole)["covered"] is True

        # ...while scoping to the CFA Level II deck (the old behaviour) excludes
        # the sibling ethics deck entirely.
        assert scoped["caption"]["gradedReviews"] == 0
        assert _ethics_topic(scoped)["gradedReviews"] == 0
        assert _ethics_topic(scoped)["covered"] is False
    finally:
        col.close()


def test_home_payload_scores_whole_collection() -> None:
    col = _empty_col()
    try:
        col.decks.id(MAIN_DECK)
        ethics = DeckId(col.decks.id(ETHICS_DECK))
        _seed_reviewed(col, ethics, "los::ethics", n=2, reviews=4)

        home = mediasrv._cfa_home_payload(col)
        # The Home dashboard (which also feeds the concept map via getCfaHomeView)
        # reflects the ethics-pair reviews rather than 0.
        assert home["caption"]["gradedReviews"] == 8
        assert _ethics_topic(home)["gradedReviews"] == 8
        # Heading still reads as the exam, not a raw sibling deck name.
        assert home["deckName"] == MAIN_DECK
    finally:
        col.close()
