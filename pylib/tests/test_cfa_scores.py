# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Feature 6: the three honest CFA scores.

Each score is a RANGE with an enforced give-up rule — never a bare number:

* Memory      — recall probability, **exam-weighted** across topics (the
                weighted-mean-by-topic-weight fix).
* Performance — P(correct on a new question), a Wilson interval on
                first-exposure accuracy.
* Readiness   — a Wilson 95% CI on estimated exam accuracy, ALWAYS shown (never
                abstains): ~0–100% with no data, tightening as questions accrue.
                Carries the standing "not validated against real exam data" label.

Pure-function tests pin the maths; collection-backed tests pin the three output
shapes end-to-end.
"""

from __future__ import annotations

import time

from anki import cfa
from anki.cards import CardId
from anki.collection import Collection
from anki.decks import DeckId
from tests.shared import getEmptyCol

DAY = 86_400


# =============================================================================
# Pure-function maths
# =============================================================================


def test_weighted_range_is_dominated_by_high_weight_topic():
    # Same two values, but nearly all the weight on the high value: the weighted
    # mean must sit far above the flat (unweighted) mean of 0.5.
    point, low, high = cfa._weighted_range([(0.9, 0.9), (0.1, 0.1)])
    assert point == 0.9 * 0.9 + 0.1 * 0.1  # == 0.82
    assert point > 0.5  # flat mean would be exactly 0.5
    assert 0.0 <= low <= point <= high <= 1.0


def test_weighted_range_zero_weights_fall_back_to_flat_mean():
    point, _low, _high = cfa._weighted_range([(0.9, 0.0), (0.1, 0.0)])
    assert point == 0.5  # equal weighting when no exam weights exist


def test_wilson_brackets_rate_and_narrows_with_more_data():
    p_small, lo_s, hi_s = cfa._wilson(15, 30)  # 50% on 30 trials
    p_big, lo_b, hi_b = cfa._wilson(500, 1000)  # 50% on 1000 trials
    assert p_small == 0.5 and p_big == 0.5
    for lo, p, hi in ((lo_s, p_small, hi_s), (lo_b, p_big, hi_b)):
        assert 0.0 <= lo <= p <= hi <= 1.0
    assert (hi_b - lo_b) < (hi_s - lo_s), "interval narrows with more evidence"


# =============================================================================
# Collection helpers
# =============================================================================


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

    ``first_ease`` gives the ease of each card's FIRST graded review (drives the
    performance score); the remaining reviews are all Good (ease 3)."""
    import json

    cids = [
        _add_card(col, deck_id, notetype, f"{topic}-{i}", [f"{topic}::r1"])
        for i in range(n_cards)
    ]
    col.sched.set_due_date(cids, "0")  # -> review cards, due today
    data = json.dumps({"s": stability, "d": 5.0, "lrt": now - DAY})
    col.db.executemany(
        "update cards set data=?, ivl=? where id=?", [(data, 20, c) for c in cids]
    )

    # Space each card's reviews on DISTINCT days (one review per card per day —
    # the realistic review-card case) so the shared engine's (card, day)
    # de-duplication is a no-op here and the raw and de-duplicated counts agree.
    # ``base_ms`` starts ``reviews_each`` days before ``now``; ``j`` selects the
    # day (j=0 the oldest, i.e. the first exposure); ``uid`` is a small,
    # globally-unique within-day offset that never crosses a day boundary.
    day_ms = DAY * 1000
    base_ms = now * 1000 - reviews_each * day_ms
    uid = col.db.scalar("select count(*) from revlog") or 0
    rows = []
    for idx, c in enumerate(cids):
        for j in range(reviews_each):
            ease = first_ease[idx] if j == 0 else 3
            # id, cid, usn, ease, ivl, lastIvl, factor, time, type(review)
            rows.append((base_ms + j * day_ms + uid, c, -1, ease, 10, 5, 2500, 1000, 1))
            uid += 1
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return cids


def _seed_rich(col: Collection) -> DeckId:
    """A collection with enough evidence that all three scores are non-abstaining:
    two exam-weighted topics (high-weight/strong, low-weight/weak), 40 first
    exposures (30 correct, 10 wrong), 240 graded reviews, full coverage."""
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    # topica: heavy weight, strong memory. 20 cards, first 10 correct + last 10.
    _seed_topic(
        col,
        deck,
        nt,
        "los::topica",
        20,
        stability=2000.0,
        reviews_each=6,
        first_ease=[3] * 20,
        now=now,
    )
    # topicb: light weight, weak memory. 20 cards, first 10 correct, 10 wrong.
    _seed_topic(
        col,
        deck,
        nt,
        "los::topicb",
        20,
        stability=8.0,
        reviews_each=6,
        first_ease=[3] * 10 + [1] * 10,
        now=now,
    )
    cfa.set_exam_config(
        col,
        exam_date="2026-12-01",
        topic_weights={"los::topica": 0.9, "los::topicb": 0.1},
    )
    return deck


# =============================================================================
# Memory — weighted-mean-by-topic-weight fix
# =============================================================================


def test_memory_score_is_exam_weighted_not_flat():
    col = getEmptyCol()
    deck = _seed_rich(col)

    score = cfa.memory_score(col, deck_id=deck)
    assert not score.abstain, score.reason
    assert score.point is not None
    # Range shape: never a bare number.
    assert score.range_low <= score.point <= score.range_high

    by_topic = {t.topic: t for t in score.topics}
    r_a = by_topic["los::topica"].avg_r
    r_b = by_topic["los::topicb"].avg_r
    assert r_a > r_b, "strong topic must have higher retrievability"

    flat_mean = (r_a + r_b) / 2
    weighted = 0.9 * r_a + 0.1 * r_b
    # The headline number tracks the exam-weighted mean, NOT the flat average.
    assert abs(score.point - weighted) < 1e-6
    assert score.point > flat_mean
    col.close()


def test_memory_score_abstains_without_enough_reviews():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _seed_topic(
        col,
        deck,
        nt,
        "los::topica",
        3,
        stability=100.0,
        reviews_each=2,
        first_ease=[3, 3, 3],
        now=now,
    )
    cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights={"los::topica": 1.0})
    score = cfa.memory_score(col, deck_id=deck)
    assert score.abstain
    assert score.point is None
    assert "not enough data" in score.reason
    col.close()


# =============================================================================
# Performance — P(correct on a new question)
# =============================================================================


def test_performance_score_shape_and_first_exposure_rate():
    col = getEmptyCol()
    deck = _seed_rich(col)

    perf = cfa.performance_score(col, deck_id=deck)
    assert not perf.abstain, perf.reason
    assert perf.first_exposures == 40
    assert perf.correct == 30  # 30 of 40 first exposures were ease>=2
    # Range shape: raw rate 0.75 bracketed by a Wilson interval, no bare number.
    assert perf.point is not None
    assert abs(perf.point - 0.75) < 1e-9
    assert perf.range_low < perf.point < perf.range_high
    assert 0.0 <= perf.range_low and perf.range_high <= 1.0
    col.close()


def test_performance_score_abstains_below_threshold():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _seed_topic(
        col,
        deck,
        nt,
        "los::topica",
        5,
        stability=100.0,
        reviews_each=1,
        first_ease=[3, 3, 3, 1, 1],
        now=now,
    )
    perf = cfa.performance_score(col, deck_id=deck)
    assert perf.abstain
    assert perf.point is None
    assert perf.first_exposures == 5
    assert "not enough data" in perf.reason
    col.close()


# =============================================================================
# Readiness — a Wilson 95% CI on estimated exam accuracy, always shown
# =============================================================================


def test_readiness_score_shape_is_a_ci_and_labelled():
    col = getEmptyCol()
    deck = _seed_rich(col)

    ready = cfa.readiness_score(col, deck_id=deck)
    assert ready.label == "not validated against real exam data"
    # Always shown — never abstains, empty reason.
    assert not ready.abstain and ready.reason == ""
    assert ready.point is not None
    # A genuine CI: the interval contains the point and stays in [0, 1].
    assert ready.range_low <= ready.point <= ready.range_high
    assert 0.0 <= ready.range_low and ready.range_high <= 1.0
    # Transparent about what fed it.
    assert ready.memory_point is not None and ready.performance_point is not None
    col.close()


def _readiness_band(n_cards: int, correct: int) -> tuple[float, float, float]:
    """Readiness (point, low, high) for a single exam-weighted topic seeded with
    ``n_cards`` first exposures, ``correct`` of them correct. Fresh collection
    each call so the two comparison points are independent."""
    col = getEmptyCol()
    try:
        now = int(time.time())
        nt = col.models.by_name("Basic")
        deck = col.decks.id("CFA")
        first_ease = [3] * correct + [1] * (n_cards - correct)
        _seed_topic(
            col,
            deck,
            nt,
            "los::topica",
            n_cards,
            stability=100.0,
            reviews_each=1,
            first_ease=first_ease,
            now=now,
        )
        cfa.set_exam_config(
            col, exam_date="2026-12-01", topic_weights={"los::topica": 1.0}
        )
        ready = cfa.readiness_score(col, deck_id=deck)
        assert ready.point is not None
        return ready.point, ready.range_low, ready.range_high
    finally:
        col.close()


def test_readiness_band_narrows_as_first_exposures_grow():
    # Same ~70% accuracy, but ten times the questions: the Wilson 95% CI must
    # narrow honestly as the number of first exposures grows (~1/sqrt(n)).
    p_small, lo_s, hi_s = _readiness_band(30, 21)
    p_big, lo_b, hi_b = _readiness_band(300, 210)
    for lo, p, hi in ((lo_s, p_small, hi_s), (lo_b, p_big, hi_b)):
        assert 0.0 <= lo <= p <= hi <= 1.0
    assert (hi_b - lo_b) < (hi_s - lo_s), "CI narrows as first exposures grow"


def test_readiness_never_abstains_even_when_an_input_abstains():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    # Far too few graded reviews for memory (it abstains), yet readiness is
    # ALWAYS shown as a Wilson CI — it never inherits the abstention any more.
    _seed_topic(
        col,
        deck,
        nt,
        "los::topica",
        35,
        stability=100.0,
        reviews_each=1,
        first_ease=[3] * 35,
        now=now,
    )
    cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights={"los::topica": 1.0})
    assert cfa.memory_score(col, deck_id=deck).abstain, "memory abstains here"

    ready = cfa.readiness_score(col, deck_id=deck)
    assert not ready.abstain
    assert ready.reason == ""
    assert ready.point is not None
    assert ready.range_low <= ready.point <= ready.range_high
    assert 0.0 <= ready.range_low and ready.range_high <= 1.0
    assert ready.label == "not validated against real exam data"
    col.close()
