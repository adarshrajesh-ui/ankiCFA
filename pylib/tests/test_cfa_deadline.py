# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""End-to-end tests for the CFA deadline-retention feature (DOK-4).

These drive ``anki.cfa_deadline.deadline_retention`` against a real collection.
The wrapper prefers the read-only Rust ``DeadlineRetention`` RPC and falls back
to an equivalent read-only SQL computation (using the same engine FSRS
retrievability function evaluated at the exam instant) when the RPC binding has
not been compiled into the running backend yet. Either way the observable
behaviour asserted here — ordering by predicted exam-day recall, deadline-capped
intervals, and read-only-ness — is identical.
"""

from __future__ import annotations

import json
import time

from anki import cfa, cfa_deadline
from anki.cards import CardId
from anki.collection import Collection
from anki.decks import DeckId
from tests.shared import getEmptyCol

QUEUE_TYPE_REVIEW = 2
DAY = 86_400


def _add_card(col: Collection, deck_id: DeckId, notetype, front: str) -> CardId:
    note = col.new_note(notetype)
    note["Front"] = front
    note["Back"] = "answer"
    col.add_note(note, deck_id)
    return col.find_cards(f"nid:{note.id}")[0]


def _add_review_card(
    col: Collection,
    deck_id: DeckId,
    notetype,
    front: str,
    *,
    stability: float | None,
    interval: int,
    now: int,
    lrt_days_ago: int = 1,
) -> CardId:
    """Create a review card, due today, with an FSRS memory state (stability +
    difficulty) last reviewed ``lrt_days_ago`` days ago and stored interval
    ``interval``. ``stability=None`` models a card with no FSRS memory state."""
    cid = _add_card(col, deck_id, notetype, front)
    col.sched.set_due_date([cid], "0")  # -> review card, due today
    if stability is None:
        data = ""
    else:
        data = json.dumps({"s": stability, "d": 5.0, "lrt": now - lrt_days_ago * DAY})
    col.db.executemany(
        "update cards set data=?, ivl=? where id=?",
        [(data, interval, cid)],
    )
    return cid


def _seconds(now: int, days: int) -> int:
    return now + days * DAY


# --- ordering ----------------------------------------------------------------


def test_orders_by_predicted_recall_weakest_first():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    # Identical interval / review-age; only stability differs. Lower stability =>
    # lower retrievability at the exam => must rank first.
    strong = _add_review_card(
        col, deck, nt, "strong", stability=1000.0, interval=20, now=now, lrt_days_ago=10
    )
    weak = _add_review_card(
        col, deck, nt, "weak", stability=3.0, interval=20, now=now, lrt_days_ago=10
    )

    res = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 14), now=now
    )
    assert list(res.card_ids) == [weak, strong], "weaker card ranks first"
    assert res.predicted_recall[0] < res.predicted_recall[1]
    assert all(0.0 <= r <= 1.0 for r in res.predicted_recall)
    col.close()


def test_never_reviewed_card_surfaces_first():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    strong = _add_review_card(
        col, deck, nt, "strong", stability=500.0, interval=15, now=now
    )
    fresh = _add_review_card(
        col, deck, nt, "fresh", stability=None, interval=15, now=now
    )

    res = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 20), now=now
    )
    assert res.card_ids[0] == fresh, "card with no memory state is weakest"
    assert res.predicted_recall[0] == 0.0
    assert res.card_ids[1] == strong
    col.close()


# --- deadline-capped interval ------------------------------------------------


def test_suggested_interval_is_capped_at_days_to_exam():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _add_review_card(col, deck, nt, "c", stability=100.0, interval=30, now=now)

    near = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 5), now=now
    )
    assert near.suggested_interval_days == [5], "30-day interval capped to 5"

    far = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 100), now=now
    )
    assert far.suggested_interval_days == [30], "far exam keeps the FSRS interval"
    col.close()


def test_past_exam_caps_interval_at_zero():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _add_review_card(col, deck, nt, "c", stability=50.0, interval=30, now=now)

    res = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, -3), now=now
    )
    assert len(res) == 1
    assert res.suggested_interval_days == [0], "past exam -> zero-day cap"
    col.close()


# --- edge cases + read-only --------------------------------------------------


def test_empty_deck_returns_empty():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    _add_review_card(
        col, col.decks.id("CFA"), nt, "c", stability=50.0, interval=30, now=now
    )
    empty = col.decks.id("Empty")

    res = cfa_deadline.deadline_retention(
        col, deck_id=empty, exam_date=_seconds(now, 30), now=now
    )
    assert list(res.card_ids) == []
    assert list(res.predicted_recall) == []
    assert list(res.suggested_interval_days) == []
    col.close()


def test_fetch_limit_truncates_after_sorting():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _add_review_card(
        col, deck, nt, "strong", stability=1000.0, interval=20, now=now, lrt_days_ago=10
    )
    weak = _add_review_card(
        col, deck, nt, "weak", stability=3.0, interval=20, now=now, lrt_days_ago=10
    )

    res = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 14), fetch_limit=1, now=now
    )
    assert list(res.card_ids) == [weak], "only the single weakest card is returned"
    col.close()


def test_is_read_only_and_adds_no_undo_step():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    cid = _add_review_card(col, deck, nt, "c", stability=10.0, interval=12, now=now)

    # Raw DB writes in _add_review_card clear the undo queue, so establish a
    # fresh undoable op to anchor the "analysis adds no undo step" assertion.
    col.sched.set_due_date([cid], "0")
    before = col.get_card(cid)
    undo_before = col.undo_status().undo
    assert undo_before, "precondition: there is an undoable op"

    r1 = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 10), now=now
    )
    r2 = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 10), now=now
    )
    assert list(r1.card_ids) == list(r2.card_ids), "idempotent"

    # The card is untouched and no new undo entry was pushed by the analysis.
    after = col.get_card(cid)
    assert (before.due, before.queue, before.ivl) == (after.due, after.queue, after.ivl)
    assert after.queue == QUEUE_TYPE_REVIEW
    assert col.undo_status().undo == undo_before, "analysis must add no undo step"

    # And the pre-existing undo target is still usable.
    col.undo()
    col.close()


# --- item5 / MEDIUM #8: wrapper that also ranks NEW cards ---------------------
#
# ``cfa_deadline.deadline_retention`` ranks only DUE cards, so a fresh all-new
# deck dead-ends on an empty table. ``cfa.deadline_retention_with_new`` wraps it
# (without modifying it) and merges in NEW cards as recall 0.0 (weakest first).


def test_fresh_all_new_deck_ranks_via_wrapper():
    # 5B: the exact defect — an all-NEW deck yields NOTHING from the due-only
    # engine, but the wrapper returns a non-empty, weakest-first ranking.
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    new_ids = [_add_card(col, deck, nt, f"new-{i}") for i in range(4)]
    assert len(col.find_cards("deck:CFA is:new")) == 4
    assert len(col.find_cards("deck:CFA is:due")) == 0

    due_only = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 30), now=now
    )
    assert len(due_only) == 0, "precondition: due-only engine sees no cards"

    res = cfa.deadline_retention_with_new(
        col, deck_id=deck, exam_date=_seconds(now, 30), now=now
    )
    assert len(res) == 4, "wrapper surfaces every new card"
    assert set(res.card_ids) == set(new_ids)
    assert all(r == 0.0 for r in res.predicted_recall), "new cards are weakest"
    assert res.predicted_recall == sorted(res.predicted_recall), "weakest-first"
    assert res.suggested_interval_days == [0, 0, 0, 0], "new cards carry no ivl"
    # Deterministic tie-break: equal recall -> ascending card id.
    assert list(res.card_ids) == sorted(new_ids)
    col.close()


def test_wrapper_ranks_new_before_due():
    # A mix: new cards (recall 0.0) must sort ABOVE a well-remembered due card.
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    strong = _add_review_card(
        col, deck, nt, "strong", stability=1000.0, interval=20, now=now, lrt_days_ago=1
    )
    new_a = _add_card(col, deck, nt, "new-a")
    new_b = _add_card(col, deck, nt, "new-b")

    res = cfa.deadline_retention_with_new(
        col, deck_id=deck, exam_date=_seconds(now, 14), now=now
    )
    assert len(res) == 3, "new + due cards all ranked, none dropped"
    assert set(res.card_ids) == {strong, new_a, new_b}
    # The two new cards (0.0) come first, ascending id; the strong due card last.
    assert list(res.card_ids) == [new_a, new_b, strong]
    assert res.predicted_recall[0] == 0.0 and res.predicted_recall[1] == 0.0
    assert res.predicted_recall[2] > 0.0
    col.close()


def test_wrapper_no_double_count_and_due_only_parity():
    # With NO new cards the wrapper is identical to the due-only engine (no
    # regression), and no card is ever counted twice.
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _add_review_card(
        col, deck, nt, "a", stability=1000.0, interval=20, now=now, lrt_days_ago=10
    )
    _add_review_card(
        col, deck, nt, "b", stability=3.0, interval=20, now=now, lrt_days_ago=10
    )
    assert len(col.find_cards("deck:CFA is:new")) == 0

    due = cfa_deadline.deadline_retention(
        col, deck_id=deck, exam_date=_seconds(now, 14), now=now
    )
    res = cfa.deadline_retention_with_new(
        col, deck_id=deck, exam_date=_seconds(now, 14), now=now
    )
    assert list(res.card_ids) == list(due.card_ids), "identical ordering"
    assert res.predicted_recall == due.predicted_recall
    assert res.suggested_interval_days == due.suggested_interval_days
    assert len(set(res.card_ids)) == len(res.card_ids), "no duplicates"
    col.close()


def test_wrapper_fetch_limit_applies_to_combined_set():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _add_review_card(col, deck, nt, "due", stability=1000.0, interval=20, now=now)
    new_a = _add_card(col, deck, nt, "new-a")
    _add_card(col, deck, nt, "new-b")

    res = cfa.deadline_retention_with_new(
        col, deck_id=deck, exam_date=_seconds(now, 14), fetch_limit=1, now=now
    )
    assert list(res.card_ids) == [new_a], "single weakest of the combined set"
    col.close()


def test_wrapper_only_ranks_requested_deck():
    # New cards in a sibling deck must not leak into another deck's ranking.
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    cfa_deck = col.decks.id("CFA")
    other = col.decks.id("Other")
    mine = _add_card(col, cfa_deck, nt, "mine")
    _add_card(col, other, nt, "theirs")

    res = cfa.deadline_retention_with_new(
        col, deck_id=cfa_deck, exam_date=_seconds(now, 30), now=now
    )
    assert list(res.card_ids) == [mine]
    col.close()
