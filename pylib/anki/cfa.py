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

import math
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


def _weighted_range(pairs: list[tuple[float, float]]) -> tuple[float, float, float]:
    """(point, low, high) = weighted mean +/- weighted stdev, clamped to [0, 1].

    Each pair is ``(value, weight)``. The overall memory score is weighted by
    each topic's exam weight so a high-weight topic you know well cannot be
    masked by a low-weight topic you know poorly (and vice versa) — this is the
    weighted-mean-by-topic-weight fix. Falls back to an equal-weight mean when
    every weight is zero (e.g. topics were derived, not configured)."""
    total_w = sum(w for _v, w in pairs)
    if total_w <= 0:
        return _range([v for v, _w in pairs])
    point = sum(v * w for v, w in pairs) / total_w
    if len(pairs) > 1:
        var = sum(w * (v - point) ** 2 for v, w in pairs) / total_w
        spread = math.sqrt(var)
    else:
        spread = 0.0
    return point, max(0.0, point - spread), min(1.0, point + spread)


def _wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(point, low, high) Wilson score interval for a binomial proportion.

    Point is the raw success rate; low/high are the two-sided ``z`` (default
    95%) Wilson bounds, which stay inside [0, 1] and widen honestly when the
    sample is small — the right shape for "how sure are we about this rate"."""
    phat = successes / n
    denom = 1.0 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt(phat * (1.0 - phat) / n + z * z / (4 * n * n)) / denom
    return phat, max(0.0, center - margin), min(1.0, center + margin)


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
    # Weighted-mean-by-topic-weight fix: the overall recall is the exam-weighted
    # mean of covered topics' retrievability, not a flat average, so high-weight
    # topics drive the headline number. Topics with no configured weight fall
    # back to equal weighting inside _weighted_range.
    covered = [t for t in topics if t.covered and t.avg_r is not None]
    if reason is None and covered:
        point, low, high = _weighted_range(
            [(t.avg_r, t.weight) for t in covered if t.avg_r is not None]
        )
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


# =============================================================================
# Honest performance score — P(correct on a NEW question)
# =============================================================================
#
# "New question" is proxied by the FIRST graded review of each card: the one
# time you answered a prompt with no recent study of it. The success rate on
# those first exposures is the most defensible estimate we have of how you would
# do on an unseen exam item, reported as a Wilson interval (never a bare number).

# Anki ease scale: 1=Again (lapse/incorrect), 2=Hard, 3=Good, 4=Easy. Anything
# other than Again counts as a successful recall.
_CORRECT_EASE = 2
# Give-up rule: below this many first exposures the sample is too thin to quote.
MIN_FIRST_EXPOSURES = 30


@dataclass
class PerformanceScore:
    abstain: bool
    reason: str
    # P(correct on a new question), as a RANGE. None when abstaining.
    point: Optional[float]
    range_low: Optional[float]
    range_high: Optional[float]
    # Evidence.
    first_exposures: int
    correct: int
    computed_at: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def performance_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> PerformanceScore:
    """Estimate P(correct on a new question) from first-exposure accuracy.

    For every card in scope we take its earliest graded review (``ease > 0``)
    and count it correct when ``ease >= 2`` (anything but *Again*). The rate is
    reported as a Wilson 95% interval; below ``MIN_FIRST_EXPOSURES`` first
    exposures the give-up rule fires and no number is shown."""
    now_ts = now_ts if now_ts is not None else int(time.time())
    computed_at = datetime.fromtimestamp(now_ts).isoformat(timespec="seconds")

    if deck_id is not None:
        did_list = col.decks.deck_and_child_ids(DeckId(int(deck_id)))
        deck_filter = "c.did in (%s)" % ",".join(str(int(d)) for d in did_list)
    else:
        deck_filter = "1"

    # First graded review per card (min revlog id == earliest), with its ease.
    rows: list[Any] = col.db.all(
        f"""
        select r.ease
        from revlog r
        join cards c on r.cid = c.id
        join (
            select cid, min(id) as mid from revlog where ease > 0 group by cid
        ) first on first.cid = r.cid and first.mid = r.id
        where {deck_filter}
        """
    )
    first_exposures = len(rows)
    correct = sum(1 for (ease,) in rows if ease >= _CORRECT_EASE)

    if first_exposures < MIN_FIRST_EXPOSURES:
        return PerformanceScore(
            abstain=True,
            reason=(
                "not enough data: "
                f"{first_exposures} first-seen questions "
                f"(need {MIN_FIRST_EXPOSURES})"
            ),
            point=None,
            range_low=None,
            range_high=None,
            first_exposures=first_exposures,
            correct=correct,
            computed_at=computed_at,
        )

    point, low, high = _wilson(correct, first_exposures)
    return PerformanceScore(
        abstain=False,
        reason="",
        point=point,
        range_low=low,
        range_high=high,
        first_exposures=first_exposures,
        correct=correct,
        computed_at=computed_at,
    )


# =============================================================================
# Honest readiness score — P(pass), deliberately wide, uncalibrated
# =============================================================================
#
# Readiness fuses memory (what you retain) and performance (how you do on fresh
# questions) into a coarse P(pass). Uncovered syllabus is treated as guessing on
# a 3-choice item. The band is widened well beyond the statistical intervals and
# carries a standing caveat because it has never been checked against a real
# CFA result — see READINESS_LABEL.

READINESS_LABEL = "not validated against real exam data"
# Rough fraction-correct needed to pass; NOT the official minimum passing score.
_MPS = 0.65
# Logistic steepness mapping estimated exam accuracy -> P(pass).
_READINESS_K = 8.0
# Guess rate on an unstudied 3-choice item.
_GUESS_RATE = 1.0 / 3.0
# Extra ± band added on top of the propagated statistical interval to reflect
# model uncertainty (this is a heuristic, not a calibrated model).
_READINESS_MARGIN = 0.15


def _pass_prob(accuracy: float) -> float:
    return 1.0 / (1.0 + math.exp(-_READINESS_K * (accuracy - _MPS)))


@dataclass
class ReadinessScore:
    abstain: bool
    reason: str
    # P(pass) as a wide RANGE. None when abstaining.
    point: Optional[float]
    range_low: Optional[float]
    range_high: Optional[float]
    # Standing honesty caveat, always present.
    label: str
    # What it was built from (for transparency in the UI).
    memory_point: Optional[float]
    performance_point: Optional[float]
    coverage_pct: float
    computed_at: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def readiness_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> ReadinessScore:
    """Combine memory + performance + coverage into a wide, uncalibrated P(pass).

    Abstains (give-up rule) whenever either input score abstains — a readiness
    number is only as trustworthy as the two scores beneath it."""
    now_ts = now_ts if now_ts is not None else int(time.time())
    computed_at = datetime.fromtimestamp(now_ts).isoformat(timespec="seconds")

    mem = memory_score(col, deck_id=deck_id, now_ts=now_ts)
    perf = performance_score(col, deck_id=deck_id, now_ts=now_ts)

    if mem.abstain or perf.abstain:
        why = []
        if mem.abstain:
            why.append(f"memory ({mem.reason})")
        if perf.abstain:
            why.append(f"performance ({perf.reason})")
        return ReadinessScore(
            abstain=True,
            reason="not enough data to estimate readiness: " + "; ".join(why),
            point=None,
            range_low=None,
            range_high=None,
            label=READINESS_LABEL,
            memory_point=mem.point,
            performance_point=perf.point,
            coverage_pct=mem.coverage_pct,
            computed_at=computed_at,
        )

    cov = mem.coverage_pct

    def _acc(m: float, p: float) -> float:
        # Blend recall and fresh-question accuracy over covered syllabus; the
        # uncovered fraction contributes a guess.
        return cov * (0.5 * m + 0.5 * p) + (1.0 - cov) * _GUESS_RATE

    assert mem.point is not None and perf.point is not None
    assert mem.range_low is not None and perf.range_low is not None
    assert mem.range_high is not None and perf.range_high is not None
    acc_point = _acc(mem.point, perf.point)
    acc_low = _acc(mem.range_low, perf.range_low)
    acc_high = _acc(mem.range_high, perf.range_high)

    point = _pass_prob(acc_point)
    low = max(0.0, _pass_prob(acc_low) - _READINESS_MARGIN)
    high = min(1.0, _pass_prob(acc_high) + _READINESS_MARGIN)

    return ReadinessScore(
        abstain=False,
        reason="",
        point=point,
        range_low=low,
        range_high=high,
        label=READINESS_LABEL,
        memory_point=mem.point,
        performance_point=perf.point,
        coverage_pct=cov,
        computed_at=computed_at,
    )
