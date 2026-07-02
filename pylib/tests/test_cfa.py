# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""End-to-end tests for the CFA fork: the read-only BuildExamQueue RPC and the
honest, give-up-aware memory score."""

from __future__ import annotations

import json
import time
from datetime import date

from anki import cfa
from anki.cards import CardId
from anki.collection import Collection
from anki.decks import DeckId
from tests.shared import getEmptyCol

QUEUE_TYPE_NEW = 0


def _add_card(
    col: Collection, deck_id: DeckId, notetype, front: str, tags: list[str]
) -> CardId:
    note = col.new_note(notetype)
    note["Front"] = front
    note["Back"] = "answer"
    note.tags = tags
    col.add_note(note, deck_id)
    return col.find_cards(f"nid:{note.id}")[0]


def _seed_studied(
    col: Collection,
    deck_id: DeckId,
    notetype,
    topic: str,
    n_cards: int,
    reviews_each: int,
) -> list[CardId]:
    """Create `n_cards` review cards under `topic` with FSRS memory state and
    `reviews_each` graded reviews apiece (direct DB writes, test-only)."""
    now = int(time.time())
    cids = [
        _add_card(col, deck_id, notetype, f"{topic}-{i}", [f"{topic}::r1"])
        for i in range(n_cards)
    ]
    col.sched.set_due_date(cids, "0")  # -> review cards, due today
    data = json.dumps({"s": 60.0, "d": 5.0, "lrt": now - 86400})
    col.db.executemany("update cards set data=? where id=?", [(data, c) for c in cids])

    base = (col.db.scalar("select coalesce(max(id), 0) from revlog") or 0) + 1
    rows = []
    n = 0
    for c in cids:
        for _ in range(reviews_each):
            # id, cid, usn, ease(>0=graded), ivl, lastIvl, factor, time, type(review)
            rows.append((base + n, c, -1, 3, 10, 5, 2500, 1000, 1))
            n += 1
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return cids


# --- BuildExamQueue RPC ------------------------------------------------------


def test_build_exam_queue_orders_by_weight():
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    low = _add_card(col, deck, nt, "q-ethics", ["los::ethics::r1"])
    high = _add_card(col, deck, nt, "q-quant", ["los::quant::r1"])
    col.sched.set_due_date([low, high], "0")

    resp = col.sched.build_exam_queue(
        deck_id=deck,
        days_to_exam=30,
        topic_weights={"los::ethics": 0.2, "los::quant": 0.9},
        fetch_limit=0,
    )
    assert list(resp.card_ids) == [high, low], "higher-weight topic first"
    assert len(resp.card_ids) == len(resp.scores)
    assert resp.scores[0] > resp.scores[1]
    col.close()


def test_build_exam_queue_content_type_multiplier():
    # Brainlift POV3: two equally-weak, equally-weighted new cards differing
    # only in content type must get DIFFERENT scores and order by multiplier.
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    formula = _add_card(col, deck, nt, "q-formula", ["los::quant::r1", "type::formula"])
    ethics = _add_card(
        col, deck, nt, "q-ethics", ["los::quant::r1", "type::ethics-rule"]
    )

    resp = col.sched.build_exam_queue(
        deck_id=deck,
        days_to_exam=30,
        topic_weights={"los::quant": 0.5},
        type_multipliers={"type::formula": 0.85, "type::ethics-rule": 1.30},
    )
    assert list(resp.card_ids) == [ethics, formula], "higher-multiplier type first"
    assert resp.scores[0] > resp.scores[1], "different types -> different scores"
    ratio = resp.scores[0] / resp.scores[1]
    assert abs(ratio - (1.30 / 0.85)) < 1e-4, "gap equals the multiplier ratio"

    # An empty multiplier map (or the convenience wrapper's default) leaves the
    # two cards tied on weight/weakness -> deterministic id order, equal scores.
    resp2 = col.sched.build_exam_queue(
        deck_id=deck,
        days_to_exam=30,
        topic_weights={"los::quant": 0.5},
        type_multipliers={},
    )
    assert abs(resp2.scores[0] - resp2.scores[1]) < 1e-6, "no multiplier -> equal"
    col.close()


def test_default_type_multipliers_are_distinct_and_present():
    # The shipped default table must cover every classifier type with distinct,
    # positive multipliers so equal-weakness cards of different types differ.
    mults = cfa.DEFAULT_TYPE_MULTIPLIERS
    assert set(mults) == {
        "type::formula",
        "type::ethics-rule",
        "type::conceptual",
        "type::multi-step-calc",
        "type::case-application",
    }
    assert all(v > 0 for v in mults.values())
    assert len(set(mults.values())) == len(mults), "multipliers must be distinct"


def test_build_exam_queue_zero_weight_and_empty_deck():
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    weighted = _add_card(col, deck, nt, "q1", ["los::quant::r1"])
    unweighted = _add_card(col, deck, nt, "q2", ["los::skip::r1"])
    col.sched.set_due_date([weighted, unweighted], "0")

    resp = col.sched.build_exam_queue(
        deck_id=deck, days_to_exam=10, topic_weights={"los::quant": 0.5}, fetch_limit=0
    )
    assert resp.card_ids[0] == weighted
    assert resp.card_ids[-1] == unweighted
    assert resp.scores[-1] == 0.0

    empty = col.decks.id("Empty")
    resp2 = col.sched.build_exam_queue(
        deck_id=empty, days_to_exam=10, topic_weights={"los::quant": 0.5}, fetch_limit=0
    )
    assert list(resp2.card_ids) == []
    assert list(resp2.scores) == []
    col.close()


def test_build_exam_queue_is_read_only_and_undo_still_works():
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    cid = _add_card(col, deck, nt, "q", ["los::quant::r1"])
    col.sched.set_due_date([cid], "0")  # undoable op -> converts New to Review

    before = col.get_card(cid)
    r1 = col.sched.build_exam_queue(
        deck_id=deck, days_to_exam=10, topic_weights={"los::quant": 1.0}
    )
    r2 = col.sched.build_exam_queue(
        deck_id=deck, days_to_exam=10, topic_weights={"los::quant": 1.0}
    )
    # Idempotent and non-mutating.
    assert list(r1.card_ids) == list(r2.card_ids)
    after = col.get_card(cid)
    assert (before.due, before.queue) == (after.due, after.queue)

    # The prior review is still the undo target (build added no undo step) and
    # undo restores the pre-review state.
    col.undo()
    assert col.get_card(cid).queue == QUEUE_TYPE_NEW
    col.close()


# --- Exam config persistence -------------------------------------------------


def test_exam_config_roundtrip_and_days_to_exam():
    col = getEmptyCol()
    cfa.set_exam_config(col, exam_date="2026-08-25", topic_weights={"los::ethics": 0.5})
    cfg = cfa.get_exam_config(col)
    assert cfg["exam_date"] == "2026-08-25"
    assert cfg["topic_weights"] == {"los::ethics": 0.5}
    assert cfa.days_to_exam(col, today=date(2026, 8, 20)) == 5
    assert cfa.days_to_exam(col, today=date(2026, 9, 1)) == 0  # clamped at 0
    col.close()


# --- Honest memory score -----------------------------------------------------


def test_memory_score_abstains_without_enough_data():
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    cfa.set_exam_config(
        col, exam_date="2026-12-01", topic_weights={"los::a": 1.0, "los::b": 1.0}
    )
    _seed_studied(col, deck, nt, "los::a", 2, 5)  # only 10 graded reviews

    score = cfa.memory_score(col, deck_id=deck)
    assert score.abstain
    assert "not enough data" in score.reason
    assert score.point is None and score.range_low is None
    col.close()


def test_memory_score_reports_range_when_sufficient():
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    cfa.set_exam_config(
        col, exam_date="2026-12-01", topic_weights={"los::a": 1.0, "los::b": 1.0}
    )
    _seed_studied(col, deck, nt, "los::a", 5, 25)  # 125 reviews
    _seed_studied(col, deck, nt, "los::b", 5, 25)  # +125 -> 250 total

    score = cfa.memory_score(col, deck_id=deck)
    assert not score.abstain, score.reason
    assert score.graded_reviews >= 200
    assert score.coverage_pct == 1.0
    assert score.point is not None
    assert score.range_low <= score.point <= score.range_high
    assert 0.0 <= score.range_low and score.range_high <= 1.0
    assert score.last_review_at is not None
    assert all(t.covered for t in score.topics)
    col.close()


def test_memory_score_abstains_when_high_weight_topic_skipped():
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    # los::b carries most of the weight but is left unstudied.
    cfa.set_exam_config(
        col, exam_date="2026-12-01", topic_weights={"los::a": 0.2, "los::b": 0.8}
    )
    _seed_studied(col, deck, nt, "los::a", 10, 25)  # 250 reviews, a covered
    _add_card(col, deck, nt, "b-unstudied", ["los::b::r1"])  # b present, no reviews

    score = cfa.memory_score(col, deck_id=deck)
    assert score.abstain
    assert "high-weight topic" in score.reason
    assert "los::b" in score.reason
    col.close()
