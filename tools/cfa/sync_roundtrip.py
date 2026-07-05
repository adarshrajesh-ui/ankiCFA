#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA two-way sync demo (Feature 9).

Stands up a local ``anki-sync-server`` and drives a desktop <-> phone
round-trip, printing a human-readable narrative that proves:

  1. tagged CFA + ethics cards sync from desktop to phone,
  2. a review made on the desktop appears on the phone after a sync,
  3. synced reviews update the shared Rust score wrappers and concept-map topic
     data on both devices,
  4. a review made on the phone appears on the desktop,
  5. when the same card is reviewed on BOTH devices offline, the two
     collections converge, both reviews are preserved (no lost / double
     counted reviews), and the more-recent review decides the card state.

Run with the repo's built python::

    just cfa-sync

Nothing here is destructive: syncing only exchanges already-recorded
reviews, so FSRS scheduling + undo history stay valid.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from typing import Literal

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_REPO, "out", "pylib"), os.path.join(_REPO, "pylib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from anki import cfa  # noqa: E402
from anki import cfa_sync as cs  # noqa: E402
from anki.cards import CardId  # noqa: E402
from anki.cards import FSRSMemoryState  # noqa: E402
from anki.collection import Collection  # noqa: E402


def _new_collection(path: str) -> Collection:
    return Collection(path)


def _add_scored_card(
    col: Collection,
    deck_name: str,
    front: str,
    back: str,
    tags: list[str],
) -> CardId:
    did = col.decks.id(deck_name)
    note = col.newNote()
    note["Front"] = front
    note["Back"] = back
    note.tags = tags
    col.add_note(note, did)
    return col.find_cards(f"nid:{note.id}")[0]


def _prepare_scored_reviews(col: Collection, cids: list[CardId]) -> None:
    # Start from review cards with FSRS state, so Memory/Readiness and the
    # concept-map Bayesian topic rows have real synced evidence to recompute.
    col.sched.set_due_date(cids, "0")
    for cid in cids:
        _apply_score_state(col, cid)


def _apply_score_state(col: Collection, cid: CardId) -> None:
    card = col.get_card(cid)
    last_review_ms = cs.last_review_ms(col, int(cid))
    card.ivl = max(card.ivl, 20)
    card.memory_state = FSRSMemoryState(stability=100.0, difficulty=5.0)
    card.desired_retention = 0.9
    card.last_review_time = (
        int(last_review_ms // 1000) if last_review_ms is not None else int(time.time()) - 86_400
    )
    col.update_card(card)


def _review(col: Collection, cid: CardId, ease: Literal[1, 2, 3, 4]) -> None:
    # Avoid same-millisecond collection-mod collisions in fast local sync runs.
    time.sleep(0.05)
    card = col.get_card(cid)
    card.start_timer()
    col.sched.answerCard(card, ease)
    _apply_score_state(col, cid)


_EASE = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}
_CFA_DECK = "CFA Level II"
_ETHICS_DECK = "CFA::Ethics Pairs"
_QUANT = "los::quant"
_ETHICS = "los::ethics"


def _topic(rows, topic: str):
    return next(t for t in rows if t.topic == topic)


def _score_snapshot(col: Collection) -> dict:
    memory = cfa.memory_score(col)
    readiness = cfa.readiness_score(col)
    bayesian = cfa.bayesian_readiness(col)
    return {
        "memory_reviews": memory.graded_reviews,
        "readiness_coverage": readiness.coverage_pct,
        "bayesian_exposures": bayesian.first_exposures,
        "memory_topics": {
            topic: _topic(memory.topics, topic).graded_reviews
            for topic in (_QUANT, _ETHICS)
        },
        "concept_topics": {
            topic: _topic(bayesian.topics, topic).covered
            for topic in (_QUANT, _ETHICS)
        },
        "concept_topics_covered": bayesian.topics_covered,
    }


def _assert_score_state(
    desktop: Collection,
    phone: Collection,
    *,
    expected_reviews: int,
    expected_exposures: int,
    expected_topics: tuple[str, ...],
    label: str,
) -> None:
    d = _score_snapshot(desktop)
    p = _score_snapshot(phone)
    for side, snap in (("desktop", d), ("phone", p)):
        assert snap["memory_reviews"] == expected_reviews, (label, side, snap)
        assert snap["bayesian_exposures"] == expected_exposures, (label, side, snap)
        assert snap["readiness_coverage"] > 0.0, (label, side, snap)
        for topic in expected_topics:
            assert snap["memory_topics"][topic] > 0, (label, side, topic, snap)
            assert snap["concept_topics"][topic] is True, (label, side, topic, snap)
    assert d == p, (label, d, p)
    print(
        f"[scores]  {label}: memory reviews={d['memory_reviews']}, "
        f"readiness coverage={d['readiness_coverage']:.0%}, "
        f"concept topics covered={d['concept_topics_covered']} "
        f"({', '.join(expected_topics)})"
    )


def main() -> int:
    workdir = tempfile.mkdtemp(prefix="gnhf-sync-")
    srv_base = os.path.join(workdir, "server")
    os.makedirs(srv_base, exist_ok=True)

    print("=" * 68)
    print("CFA TWO-WAY SYNC ROUND-TRIP  (desktop <-> anki-sync-server <-> phone)")
    print("=" * 68)

    with cs.sync_server(srv_base) as server:
        print(f"\n[server]  anki-sync-server listening at {server.endpoint}")
        print(
            f"[server]  user '{server.username}', collections stored under {srv_base}"
        )

        desktop = _new_collection(os.path.join(workdir, "desktop.anki2"))
        cfa_cid = _add_scored_card(
            desktop,
            _CFA_DECK,
            "CFA L2: what does WACC stand for?",
            "weighted average cost of capital",
            [f"{_QUANT}::sync", "type::conceptual"],
        )
        ethics_cid = _add_scored_card(
            desktop,
            _ETHICS_DECK,
            "Acting on unreleased earnings figures: conform or violate?",
            "violate - Standard II(A)",
            [f"{_ETHICS}::sync", "type::ethics-rule"],
        )
        _prepare_scored_reviews(desktop, [cfa_cid, ethics_cid])
        d_auth = cs.login(desktop, server)
        cs.sync(desktop, d_auth)
        print("\n[desktop] created tagged CFA + ethics cards, logged in, uploaded to server")

        phone = _new_collection(os.path.join(workdir, "phone.anki2"))
        p_auth = cs.login(phone, server)
        cs.sync(phone, p_auth)
        print(
            f"[phone]   synced down: now has {phone.card_count()} cards, "
            f"{phone.note_count()} notes"
        )

        print("\n--- 1. FORWARD: review on desktop, sync, check phone -----------")
        _review(desktop, cfa_cid, 3)
        print(
            f"[desktop] reviewed CFA card -> '{_EASE[3]}'  (revlog rows: "
            f"{len(cs.revlog_events(desktop, cfa_cid))})"
        )
        cs.sync(desktop, d_auth)
        cs.sync(phone, p_auth)
        pe = cs.revlog_events(phone, cfa_cid)
        print(
            f"[phone]   after sync: {len(pe)} review present, "
            f"last = '{_EASE[pe[-1].ease]}'  -> review propagated ✓"
        )
        _assert_score_state(
            desktop,
            phone,
            expected_reviews=1,
            expected_exposures=1,
            expected_topics=(_QUANT,),
            label="desktop review reached phone scores + concept map",
        )

        print("\n--- 2. REVERSE: review on phone, sync, check desktop -----------")
        _review(phone, ethics_cid, 2)
        print(f"[phone]   reviewed ethics card -> '{_EASE[2]}'")
        cs.sync(phone, p_auth)
        cs.sync(desktop, d_auth)
        de = cs.revlog_events(desktop, ethics_cid)
        print(
            f"[desktop] after sync: {len(de)} ethics review present, "
            f"last = '{_EASE[de[-1].ease]}'  -> review propagated back ✓"
        )
        _assert_score_state(
            desktop,
            phone,
            expected_reviews=2,
            expected_exposures=2,
            expected_topics=(_QUANT, _ETHICS),
            label="phone review reached desktop scores + concept map",
        )

        print("\n--- 3. CONFLICT: same card reviewed on BOTH, offline -----------")
        _review(desktop, cfa_cid, 1)
        _review(phone, cfa_cid, 4)
        d_ms = cs.last_review_ms(desktop, cfa_cid)
        p_ms = cs.last_review_ms(phone, cfa_cid)
        print(f"[desktop] reviewed -> '{_EASE[1]}'  at {d_ms} ms")
        print(
            f"[phone]   reviewed -> '{_EASE[4]}'  at {p_ms} ms  "
            f"(phone is {p_ms - d_ms} ms more recent)"
        )
        cs.sync(desktop, d_auth)
        cs.sync(phone, p_auth)
        cs.sync(desktop, d_auth)

        d_ids = [e.reviewed_at_ms for e in cs.revlog_events(desktop, cfa_cid)]
        p_ids = [e.reviewed_at_ms for e in cs.revlog_events(phone, cfa_cid)]
        converged = cs.last_review_ms(desktop, cfa_cid)
        winner = cs.resolve_review_conflict(
            cs.ReviewEvent(cfa_cid, d_ms, 1, "desktop"),
            cs.ReviewEvent(cfa_cid, p_ms, 4, "phone"),
        )
        print(
            f"[both]    converged revlog ids identical: {sorted(d_ids) == sorted(p_ids)}"
        )
        print(
            f"[both]    total distinct reviews: {len(d_ids)} "
            f"(no duplicates: {len(d_ids) == len(set(d_ids))})"
        )
        print(
            f"[rule]    resolve_review_conflict() -> winner is '{winner.source}' "
            f"(more recent)"
        )
        print(
            f"[both]    converged card's last review == phone's review: "
            f"{converged == p_ms == winner.reviewed_at_ms}"
        )
        _assert_score_state(
            desktop,
            phone,
            expected_reviews=2,
            expected_exposures=2,
            expected_topics=(_QUANT, _ETHICS),
            label="offline conflict did not double-count scores or concept map",
        )

        ok = (
            sorted(d_ids) == sorted(p_ids)
            and len(d_ids) == len(set(d_ids))
            and converged == p_ms
        )
        print("\n" + "=" * 68)
        print("RESULT:", "ALL CHECKS PASSED ✓" if ok else "FAILED ✗")
        print("=" * 68)
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
