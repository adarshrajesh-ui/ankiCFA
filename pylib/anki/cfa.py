# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork: exam configuration + an *honest* per-topic memory score.

There is NO AI here — this is pure spaced-repetition statistics. The memory
score is the per-topic average FSRS retrievability R (probability of recall),
reported as a RANGE (mean +/- spread) rather than a single overconfident
number, together with how much of the syllabus is actually covered.

An enforced give-up rule means the app abstains ("not enough data") until there
is a defensible amount of evidence, and abstains outright if a high-weight
topic has been skipped. Topics are keyed by hierarchical ``los::`` tags, the
same join key the Rust ``BuildExamQueue`` engine uses.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Optional, cast

import anki.collection
from anki.decks import DeckId

TOPIC_PREFIX = "los::"
EXAM_CONFIG_KEY = "cfa_exam_config"

# --- Give-up rule (enforced) -------------------------------------------------
# No score is shown until BOTH of these hold; below either threshold the app
# reports "not enough data" instead of a number. Additionally, if any topic
# whose weight is at/above the average configured weight has no graded reviews,
# the deck has skipped a high-weight topic and we abstain regardless.
MIN_GRADED_REVIEWS = 200
MIN_TOPIC_COVERAGE = 0.50


# =============================================================================
# Exam configuration (persisted in the collection config -> syncs natively)
# =============================================================================


def set_exam_config(
    col: anki.collection.Collection,
    *,
    exam_date: str,
    topic_weights: dict[str, float],
) -> None:
    """Persist the exam date (ISO ``YYYY-MM-DD``) and topic weights.

    Stored via the collection config, which syncs natively — no new sync
    endpoint. Weights are keyed by ``los::`` tag prefix (e.g. ``los::ethics``).
    """
    col.set_config(
        EXAM_CONFIG_KEY,
        {"exam_date": exam_date, "topic_weights": dict(topic_weights)},
    )


def get_exam_config(col: anki.collection.Collection) -> Optional[dict[str, Any]]:
    return col.get_config(EXAM_CONFIG_KEY, None)


def days_to_exam(
    col: anki.collection.Collection, *, today: Optional[date] = None
) -> Optional[int]:
    """Whole days from ``today`` until the configured exam date (>= 0), or None
    if no exam date has been configured."""
    cfg = get_exam_config(col)
    if not cfg or not cfg.get("exam_date"):
        return None
    exam = date.fromisoformat(cfg["exam_date"])
    today = today or date.today()
    return max(0, (exam - today).days)


def build_exam_queue(
    col: anki.collection.Collection,
    *,
    deck_id: DeckId | int,
    today: Optional[date] = None,
    fetch_limit: int = 0,
) -> Any:
    """Convenience wrapper: build the exam queue using the persisted exam date
    and topic weights. Delegates to the read-only Rust ``BuildExamQueue`` RPC."""
    from anki.scheduler.v3 import Scheduler as V3Scheduler

    cfg = get_exam_config(col) or {}
    weights = cfg.get("topic_weights", {})
    dte = days_to_exam(col, today=today)
    return cast(V3Scheduler, col.sched).build_exam_queue(
        deck_id=int(deck_id),
        days_to_exam=dte if dte is not None else 0,
        topic_weights=weights,
        fetch_limit=fetch_limit,
    )


# =============================================================================
# Honest memory score
# =============================================================================


@dataclass
class TopicScore:
    topic: str
    weight: float
    reviewed_cards: int
    graded_reviews: int
    # Retrievability reported as a range; None until the topic has data.
    avg_r: Optional[float]
    r_low: Optional[float]
    r_high: Optional[float]
    covered: bool


@dataclass
class MemoryScore:
    # Give-up rule outcome.
    abstain: bool
    reason: str
    # Overall memory as a RANGE (never a bare number). None when abstaining.
    point: Optional[float]
    range_low: Optional[float]
    range_high: Optional[float]
    # Evidence.
    coverage_pct: float
    topics_total: int
    topics_covered: int
    graded_reviews: int
    # Freshness.
    last_review_at: Optional[str]
    computed_at: str
    # Per-topic breakdown (always populated so the UI can show gaps).
    topics: list[TopicScore] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _topic_of(tags: str, topic_prefixes: list[str]) -> Optional[str]:
    """Longest-prefix match of a card's ``los::`` tags against configured
    topics. Returns None if the card belongs to no configured topic."""
    best: Optional[str] = None
    for tag in tags.split():
        if not tag.startswith(TOPIC_PREFIX):
            continue
        for prefix in topic_prefixes:
            if tag == prefix or tag.startswith(prefix + "::"):
                if best is None or len(prefix) > len(best):
                    best = prefix
    return best


def _derive_topics(rows: list[Any]) -> list[str]:
    """When no weights are configured, derive topics as the 2-level ``los::x``
    prefix of every ``los::`` tag seen in the deck."""
    topics: set[str] = set()
    for _cid, tags, _r in rows:
        for tag in (tags or "").split():
            if tag.startswith(TOPIC_PREFIX):
                parts = tag.split("::")
                if len(parts) >= 2:
                    topics.add("::".join(parts[:2]))
    return sorted(topics)


def _range(values: list[float]) -> tuple[float, float, float]:
    """(point, low, high) = mean +/- population stdev, clamped to [0, 1]."""
    point = statistics.fmean(values)
    spread = statistics.pstdev(values) if len(values) > 1 else 0.0
    return point, max(0.0, point - spread), min(1.0, point + spread)


def _build_topic_scores(
    rows: list[Any],
    review_counts: dict[int, int],
    topic_prefixes: list[str],
    weights: dict[str, float],
) -> list[TopicScore]:
    """Group per-card (tags, R) rows into per-topic scores."""
    per_r: dict[str, list[float]] = {t: [] for t in topic_prefixes}
    per_reviews: dict[str, int] = {t: 0 for t in topic_prefixes}
    for cid, tags, r in rows:
        topic = _topic_of(tags or "", topic_prefixes)
        if topic is None:
            continue
        per_reviews[topic] += review_counts.get(cid, 0)
        if r is not None:
            per_r[topic].append(float(r))

    scores: list[TopicScore] = []
    for topic in topic_prefixes:
        r_values = per_r[topic]
        avg_r = r_low = r_high = None
        if r_values:
            avg_r, r_low, r_high = _range(r_values)
        scores.append(
            TopicScore(
                topic=topic,
                weight=float(weights.get(topic, 0.0)),
                reviewed_cards=len(r_values),
                graded_reviews=per_reviews[topic],
                avg_r=avg_r,
                r_low=r_low,
                r_high=r_high,
                covered=per_reviews[topic] > 0 and bool(r_values),
            )
        )
    return scores


def _giveup_reason(
    topics: list[TopicScore],
    total_reviews: int,
    coverage_pct: float,
    weights: dict[str, float],
) -> Optional[str]:
    """Return an abstain reason if the give-up rule fires, else None."""
    if not topics:
        return "not enough data: no topics found (tag notes with los::…)"
    if total_reviews < MIN_GRADED_REVIEWS or coverage_pct < MIN_TOPIC_COVERAGE:
        return (
            "not enough data: "
            f"{total_reviews} graded reviews (need {MIN_GRADED_REVIEWS}), "
            f"{coverage_pct * 100:.0f}% topic coverage (need "
            f"{MIN_TOPIC_COVERAGE * 100:.0f}%)"
        )
    # A skipped high-weight topic invalidates the whole score.
    if weights:
        positive = [w for w in weights.values() if w > 0]
        threshold = statistics.fmean(positive) if positive else 0.0
        skipped = sorted(
            t.topic
            for t in topics
            if t.weight >= threshold and t.weight > 0 and not t.covered
        )
        if skipped:
            return f"high-weight topic(s) skipped, no score: {', '.join(skipped)}"
    return None


def memory_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> MemoryScore:
    """Compute the honest, give-up-aware memory score for a deck (or the whole
    collection when ``deck_id`` is None).

    Retrievability is computed in bulk by the same FSRS SQL helper the Rust
    engine uses, so it is consistent and fast on large decks.
    """
    now_ts = now_ts if now_ts is not None else int(time.time())
    computed_at = datetime.fromtimestamp(now_ts).isoformat(timespec="seconds")

    # Deck scoping (deck + subdecks).
    if deck_id is not None:
        did_list = col.decks.deck_and_child_ids(DeckId(int(deck_id)))
        deck_filter = "c.did in (%s)" % ",".join(str(int(d)) for d in did_list)
    else:
        deck_filter = "1"

    today = col.sched.today
    next_day_at = col.sched.day_cutoff

    # (card id, tags, retrievability) for every card in scope. R is NULL for
    # cards with no FSRS memory state (never reviewed).
    rows: list[Any] = col.db.all(
        f"""
        select c.id, n.tags,
          extract_fsrs_retrievability(
            c.data,
            case when c.odue != 0 then c.odue else c.due end,
            c.ivl, ?, ?, ?)
        from cards c join notes n on c.nid = n.id
        where {deck_filter}
        """,
        today,
        next_day_at,
        now_ts,
    )

    # Graded reviews per card (ease > 0 excludes manual reschedules).
    review_counts: dict[int, int] = {
        row[0]: row[1]
        for row in col.db.all(
            f"""
            select c.id, count(*)
            from revlog r join cards c on r.cid = c.id
            where {deck_filter} and r.ease > 0
            group by c.id
            """
        )
    }

    # Freshness: newest graded review in scope (revlog id is a ms timestamp).
    last_ms: Optional[int] = col.db.scalar(
        f"""
        select max(r.id) from revlog r join cards c on r.cid = c.id
        where {deck_filter} and r.ease > 0
        """
    )
    last_review_at = (
        datetime.fromtimestamp(last_ms / 1000).isoformat(timespec="seconds")
        if last_ms
        else None
    )

    cfg = get_exam_config(col) or {}
    weights: dict[str, float] = cfg.get("topic_weights", {})
    topic_prefixes = sorted(weights.keys()) if weights else _derive_topics(rows)

    topics = _build_topic_scores(rows, review_counts, topic_prefixes, weights)
    total_reviews = sum(review_counts.values())
    topics_total = len(topic_prefixes)
    topics_covered = sum(1 for t in topics if t.covered)
    coverage_pct = (topics_covered / topics_total) if topics_total else 0.0

    reason = _giveup_reason(topics, total_reviews, coverage_pct, weights)
    covered_means = [t.avg_r for t in topics if t.covered and t.avg_r is not None]
    if reason is None and covered_means:
        point, low, high = _range([m for m in covered_means if m is not None])
    else:
        point = low = high = None

    return MemoryScore(
        abstain=reason is not None,
        reason=reason or "",
        point=point,
        range_low=low,
        range_high=high,
        coverage_pct=coverage_pct,
        topics_total=topics_total,
        topics_covered=topics_covered,
        graded_reviews=total_reviews,
        last_review_at=last_review_at,
        computed_at=computed_at,
        topics=topics,
    )
