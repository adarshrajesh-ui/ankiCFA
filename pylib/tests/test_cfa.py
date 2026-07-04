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


def test_build_exam_queue_all_decks_merges_new_cards_across_decks():
    # item2 fresh-profile fix: when the current deck is empty, exam-priority
    # falls back to a collection-wide merge. Two sibling top-level decks each
    # hold a NEW card (treated as maximally weak, R=0); the built-in Default
    # deck stays empty. A deck-scoped queue on Default is empty, but the merged
    # collection-wide queue must include BOTH new cards, weakest-first.
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    d1 = col.decks.id("CFA Level II")
    d2 = col.decks.id("CFA::Ethics Pairs")  # also creates top-level "CFA"
    quant_new = _add_card(col, d1, nt, "quant-new", ["los::quant::r1"])
    ethics_new = _add_card(col, d2, nt, "ethics-new", ["los::ethics::r1"])
    cfa.set_exam_config(
        col,
        exam_date="2026-08-25",
        topic_weights={"los::quant": 0.9, "los::ethics": 0.1},
    )

    # Deck-scoped to the empty Default deck: nothing studyable (the dead-end).
    default_id = col.decks.id("Default")
    scoped = cfa.build_exam_queue(col, deck_id=default_id, fetch_limit=0)
    assert list(scoped.card_ids) == []

    # Collection-wide: both NEW cards, higher-weight topic first.
    merged = cfa.build_exam_queue_all_decks(col, fetch_limit=0)
    assert set(merged.card_ids) == {quant_new, ethics_new}
    assert merged.card_ids[0] == quant_new, "higher-weight (quant) card first"
    assert len(merged.card_ids) == len(merged.scores)
    assert merged.scores[0] >= merged.scores[-1]

    # fetch_limit truncates the merged, already-sorted result.
    capped = cfa.build_exam_queue_all_decks(col, fetch_limit=1)
    assert capped.card_ids == [quant_new]
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


# --- item3 sub-bug 3B: canonical topic accounting ---------------------------
#
# topics_total == len(score.topics) always, and equals the canonical CFA
# syllabus (eight authored topics) regardless of which deck is in scope, so the
# UI's count == per-topic table rows == topic list.


def test_memory_score_no_config_uses_canonical_topic_total():
    # Fresh, no exam config, no cards: the total is the canonical 8 (not a
    # deck-derived 0/1), and topics_total == len(topics) (== table rows).
    col = getEmptyCol()
    deck = col.decks.id("CFA")
    assert cfa.get_exam_config(col) is None
    score = cfa.memory_score(col, deck_id=deck)
    assert score.topics_total == 8
    assert len(score.topics) == 8
    assert score.topics_covered == 0
    assert [t.topic for t in score.topics] == cfa.CANONICAL_TOPICS
    assert all(not t.covered and t.avg_r is None for t in score.topics)
    col.close()


def test_memory_score_no_config_partial_study_denominator_is_canonical():
    # Study one canonical topic heavily but with no config; the coverage
    # denominator is the canonical 8 (not 1), so coverage = 1/8 < 0.5 and the
    # give-up rule correctly abstains (the "1 -> 8 denominator" change). Exactly
    # one row is covered; the other seven render as "no data".
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _seed_studied(col, deck, nt, "los::ethics", 10, 25)  # 250 reviews, ethics only
    assert cfa.get_exam_config(col) is None

    score = cfa.memory_score(col, deck_id=deck)
    assert score.graded_reviews >= 200  # plenty of reviews ...
    assert score.topics_total == 8
    assert len(score.topics) == 8
    assert score.topics_covered == 1
    assert abs(score.coverage_pct - 1 / 8) < 1e-9
    assert score.abstain  # ... but 1/8 coverage < 0.50 -> abstain
    assert "topic coverage" in score.reason
    by = {t.topic: t for t in score.topics}
    assert by["los::ethics"].covered and by["los::ethics"].avg_r is not None
    uncovered = [t for t in score.topics if t.topic != "los::ethics"]
    assert len(uncovered) == 7
    assert all(not t.covered and t.avg_r is None for t in uncovered)
    col.close()


def test_memory_score_topic_total_deck_independent_without_config():
    # Same canonical total (8) whether scoped to the parent or a single-topic
    # subdeck; only the covered subset differs.
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    ethics_deck = col.decks.id("CFA::EthicsOnly")
    quant_deck = col.decks.id("CFA::QuantOnly")
    _seed_studied(col, ethics_deck, nt, "los::ethics", 3, 5)
    _seed_studied(col, quant_deck, nt, "los::quant", 3, 5)
    parent = col.decks.id("CFA")

    whole = cfa.memory_score(col, deck_id=parent)
    scoped = cfa.memory_score(col, deck_id=ethics_deck)
    assert whole.topics_total == scoped.topics_total == 8
    assert len(whole.topics) == len(scoped.topics) == 8
    assert whole.topics_covered == 2  # ethics + quant both in scope
    assert scoped.topics_covered == 1  # only ethics in this subdeck
    col.close()


def test_memory_score_config_topic_total_matches_configured_topics():
    # With a weight per authored topic (the seeded product) the total equals the
    # configured (== canonical) count, and topics_total == len(topics).
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    cfa.set_exam_config(
        col,
        exam_date="2026-12-01",
        topic_weights={t: 1.0 / 8 for t in cfa.CANONICAL_TOPICS},
    )
    _seed_studied(col, deck, nt, "los::ethics", 5, 25)
    score = cfa.memory_score(col, deck_id=deck)
    assert score.topics_total == 8
    assert len(score.topics) == 8
    assert score.topics_covered == 1
    col.close()


def test_topic_display_name_maps_canonical_slugs_and_falls_back():
    # Every canonical topic slug resolves to a readable CFA topic-area name (no
    # raw ``los::`` slug ever surfaces in the UI).
    expected = {
        "los::ethics": "Ethics & Professional Standards",
        "los::quant": "Quantitative Methods",
        "los::econ": "Economics",
        "los::fra": "Financial Reporting & Analysis",
        "los::corp": "Corporate Issuers",
        "los::equity": "Equity Investments",
        "los::altinv": "Alternative Investments",
        "los::portmgmt": "Portfolio Management",
    }
    for slug in cfa.CANONICAL_TOPICS:
        assert cfa.topic_display_name(slug) == expected[slug]
    # A sub-tag resolves to its top-level topic name (longest-prefix join key).
    assert (
        cfa.topic_display_name("los::fra::goodwill") == "Financial Reporting & Analysis"
    )
    # An unknown slug falls back to a title-cased, human-readable form.
    assert cfa.topic_display_name("los::my_new-topic") == "My New Topic"
    # A bare (prefix-less) slug is handled too.
    assert cfa.topic_display_name("derivatives") == "Derivatives"
