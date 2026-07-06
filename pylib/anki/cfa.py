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
from typing import TYPE_CHECKING, Any, Optional, cast

import anki.collection
from anki.decks import DeckId

if TYPE_CHECKING:
    from anki import cfa_deadline

TOPIC_PREFIX = "los::"
TYPE_PREFIX = "type::"
EXAM_CONFIG_KEY = "cfa_exam_config"

# Content-type-aware interval multipliers (Brainlift POV3). Different CFA item
# types decay at different rates, so equally-weak cards of different types
# deserve different exam-queue priority. Multipliers are relative to 1.0
# (conceptual baseline); a card with no ``type::`` tag is scored at 1.0.
#   - formula: once memorized a formula tends to stick -> lower priority
#   - ethics-rule: nuanced, easy to confuse the specifics -> higher priority
#   - conceptual: baseline
#   - multi-step-calc: procedural, needs repeated practice -> higher
#   - case-application: integrative vignette reasoning -> higher
DEFAULT_TYPE_MULTIPLIERS: dict[str, float] = {
    "type::formula": 0.85,
    "type::ethics-rule": 1.30,
    "type::conceptual": 1.00,
    "type::multi-step-calc": 1.20,
    "type::case-application": 1.15,
}

# --- Give-up rule (enforced) -------------------------------------------------
# No score is shown until BOTH of these hold; below either threshold the app
# reports "not enough data" instead of a number. Additionally, if any topic
# whose weight is at/above the average configured weight has no graded reviews,
# the deck has skipped a high-weight topic and we abstain regardless.
MIN_GRADED_REVIEWS = 200
MIN_TOPIC_COVERAGE = 0.50

# --- Canonical CFA syllabus --------------------------------------------------
# The authored CFA Level II topic areas, keyed by their ``los::<topic>`` tag
# prefix. This is the in-code source of truth for "how big is the syllabus", so
# the readiness scores agree on a single, deck-independent topic total: the
# per-topic table, the coverage denominator and the "N/total topics" caption all
# resolve to this same list no matter which deck happens to be selected.
#
# These ten prefixes are the official CFA Level II topic areas (see
# ``cfa/outline/level2_topics.json``): Ethics, Quantitative Methods, Economics,
# Financial Reporting & Analysis, Corporate Issuers, Equity, Fixed Income,
# Derivatives, Alternative Investments and Portfolio Management. Each is exactly
# the ``los::`` prefix the authored deck (``cfa/deck/*.jsonl``) tags its cards
# with, so ``sorted(weights.keys())`` matches this list when the exam config is
# seeded. (Fixed Income uses the hyphenated ``los::fixed-income`` prefix that its
# deck cards carry — matching the tag is what makes the topic count as covered.)
# The constant is what the scores fall back to when no exam weights are
# configured, instead of deriving a variable, deck-scoped list from whatever
# cards are in scope (which produced inconsistent totals — and, for the
# four-column readiness query, a crash). Keep sorted; keep in lock-step with the
# Rust ``CANONICAL_TOPICS`` in ``rslib/src/scheduler/cfa_scores.rs``.
CANONICAL_TOPICS: list[str] = [
    "los::altinv",
    "los::corp",
    "los::derivatives",
    "los::econ",
    "los::equity",
    "los::ethics",
    "los::fixed-income",
    "los::fra",
    "los::portmgmt",
    "los::quant",
]

# Human-readable CFA topic-area names for the ``los::<slug>`` tag prefixes.
# Topics are keyed internally by their ``los::`` join-key tag (see
# CANONICAL_TOPICS), but the readiness UI should read as CFA topic areas rather
# than raw slugs. This maps the bare slug (the text after ``los::``) to its
# canonical name; unknown slugs fall back to a title-cased form of the slug (see
# :func:`topic_display_name`), so a newly-authored topic is still readable
# without a code change. Presentation only — the raw tag stays the join key.
TOPIC_DISPLAY_NAMES: dict[str, str] = {
    "ethics": "Ethics & Professional Standards",
    "quant": "Quantitative Methods",
    "econ": "Economics",
    "fra": "Financial Reporting & Analysis",
    "corp": "Corporate Issuers",
    "equity": "Equity Investments",
    "fixed_income": "Fixed Income",
    "fixed-income": "Fixed Income",
    "fi": "Fixed Income",
    "derivatives": "Derivatives",
    "altinv": "Alternative Investments",
    "portmgmt": "Portfolio Management",
}


def topic_display_name(topic: str) -> str:
    """Human-readable CFA topic-area name for a ``los::<slug>`` tag prefix.

    Strips the ``los::`` prefix and maps the slug to its canonical CFA topic
    name (see :data:`TOPIC_DISPLAY_NAMES`). An unknown slug falls back to a
    title-cased form of the slug (``los::my_topic`` -> "My Topic") so a new
    topic is still readable without a code change. Purely presentational: the
    raw ``los::`` tag remains the join key everywhere else.
    """
    slug = topic[len(TOPIC_PREFIX) :] if topic.startswith(TOPIC_PREFIX) else topic
    slug = slug.split("::", 1)[0]
    if slug in TOPIC_DISPLAY_NAMES:
        return TOPIC_DISPLAY_NAMES[slug]
    words = slug.replace("_", " ").replace("-", " ").split()
    return " ".join(word.capitalize() for word in words) if words else topic


def readiness_topic_prefixes(weights: dict[str, float]) -> list[str]:
    """Topic prefixes for the CFA-readiness scores, as a canonical list.

    When exam ``weights`` are configured they are authoritative — the seeded
    product persists one weight per authored topic, so this is the canonical
    syllabus already. When no weights are configured we fall back to the fixed
    :data:`CANONICAL_TOPICS` list rather than deriving topics from the cards in
    scope, so the topic total, coverage denominator and per-topic table stay
    consistent (and deck-independent) regardless of which deck is selected."""
    return sorted(weights.keys()) if weights else list(CANONICAL_TOPICS)


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
    type_multipliers: Optional[dict[str, float]] = None,
) -> Any:
    """Convenience wrapper: build the exam queue using the persisted exam date
    and topic weights. Delegates to the read-only Rust ``BuildExamQueue`` RPC.

    ``type_multipliers`` (Brainlift POV3) defaults to
    :data:`DEFAULT_TYPE_MULTIPLIERS` so content-type-aware weighting is on by
    default; pass ``{}`` to disable it (all cards scored at 1.0)."""
    from anki.scheduler.v3 import Scheduler as V3Scheduler

    cfg = get_exam_config(col) or {}
    weights = cfg.get("topic_weights", {})
    dte = days_to_exam(col, today=today)
    if type_multipliers is None:
        type_multipliers = DEFAULT_TYPE_MULTIPLIERS
    return cast(V3Scheduler, col.sched).build_exam_queue(
        deck_id=int(deck_id),
        days_to_exam=dte if dte is not None else 0,
        topic_weights=weights,
        fetch_limit=fetch_limit,
        type_multipliers=type_multipliers,
    )


@dataclass
class ExamQueue:
    """A merged, weakest-first exam-priority queue.

    Mirrors the read-only ``BuildExamQueue`` RPC response shape (parallel
    ``card_ids`` and ``scores``) so callers can treat it interchangeably.
    """

    card_ids: list[int]
    scores: list[float]


def _top_level_deck_ids(col: anki.collection.Collection) -> list[DeckId]:
    """Ids of the top-level, non-filtered decks.

    Each top-level deck rolls up all of its subdecks (the RPC gathers with
    children), and every card belongs to exactly one top-level deck, so this is
    the right granularity to score the whole collection without double-counting.
    """
    return [
        DeckId(entry.id)
        for entry in col.decks.all_names_and_ids(
            skip_empty_default=False, include_filtered=False
        )
        if "::" not in entry.name
    ]


def build_exam_queue_all_decks(
    col: anki.collection.Collection,
    *,
    today: Optional[date] = None,
    fetch_limit: int = 0,
    type_multipliers: Optional[dict[str, float]] = None,
) -> ExamQueue:
    """Collection-wide exam-priority queue, merged across every top-level deck.

    This is the fallback for when the *current* deck has no studyable cards —
    e.g. a freshly seeded profile whose selected deck is still the empty
    built-in "Default" deck while every NEW CFA card lives in the CFA decks. It
    calls the read-only :func:`build_exam_queue` once per top-level deck (with
    its subdecks), so every studyable card — due *and* NEW (treated as maximally
    weak, R=0) — that lives in a regular deck is scored exactly once, then merges
    the per-deck results into a single weakest-first ordering (score descending,
    ties broken by ascending card id, matching the RPC's own ordering). Read-only
    throughout.

    Cards *currently* sitting in a filtered deck are excluded: filtered decks are
    skipped as scoring roots and the RPC matches on a card's home deck (``c.did``,
    which is the filtered deck while the card is pulled), so they belong to no
    top-level regular deck here. A fresh profile is therefore never a dead-end
    while studyable cards exist in the regular decks — the common case — but the
    queue can still be empty if every remaining card is off in a filtered deck.
    """
    merged: list[tuple[int, float]] = []
    for did in _top_level_deck_ids(col):
        resp = build_exam_queue(
            col,
            deck_id=did,
            today=today,
            fetch_limit=0,
            type_multipliers=type_multipliers,
        )
        merged.extend(
            zip((int(c) for c in resp.card_ids), (float(s) for s in resp.scores))
        )
    merged.sort(key=lambda cs: (-cs[1], cs[0]))
    if fetch_limit:
        merged = merged[: int(fetch_limit)]
    return ExamQueue(
        card_ids=[cid for cid, _ in merged],
        scores=[score for _, score in merged],
    )


# =============================================================================
# Deadline retention including NEW cards (fresh-profile-safe peak-on-exam-day)
# =============================================================================


def deadline_retention_with_new(
    col: anki.collection.Collection,
    *,
    deck_id: DeckId | int,
    exam_date: "cfa_deadline.ExamDate",
    fetch_limit: int = 0,
    now: Optional[int] = None,
) -> "cfa_deadline.DeadlineRetention":
    """Weakest-first exam-day ranking that ALSO includes brand-new cards.

    :func:`anki.cfa_deadline.deadline_retention` ranks only a deck's DUE cards,
    so on a fresh profile — where every CFA card is still NEW — it returns an
    empty ranking and the desktop "Peak-on-Exam-Day" view dead-ends on "No due
    cards to rank yet". This is a thin, read-only WRAPPER around that engine
    (which it does not modify): it takes the due-card ranking verbatim and then
    merges in the deck's NEW cards, whose predicted exam-day recall is treated as
    0.0 (never studied => maximally weak), so they sort to the very top of the
    weakest-first order and the table is non-empty out of the box.

    New cards carry no schedule yet, so their deadline-capped next interval is 0.
    The merged rows are re-sorted by (predicted recall ascending, card id
    ascending) — identical to the engine's own ordering. When ``fetch_limit`` is
    set, at least half of the slots are reserved for DUE cards so a large
    new-card backlog cannot crowd the genuinely-weak scheduled cards out of the
    capped view (new cards still fill every slot the due cards leave unused, so a
    fresh all-new deck is unaffected). ``used_rpc`` mirrors the underlying
    due-card engine. Never mutates the collection, so FSRS scheduling and undo
    stay valid.
    """
    from anki import cfa_deadline

    due = cfa_deadline.deadline_retention(
        col, deck_id=deck_id, exam_date=exam_date, fetch_limit=0, now=now
    )

    # NEW cards in the deck (and subdecks), using the same search-engine
    # semantics ("is:new") as the deadline module's due-card query. Exclude
    # anything already ranked as due so a card is never counted twice.
    ranked = set(due.card_ids)
    deck_name = col.decks.name(DeckId(int(deck_id)))
    escaped = cfa_deadline._escape_deck_name(deck_name)
    new_cids = [
        int(cid)
        for cid in col.find_cards(f'deck:"{escaped}" is:new')
        if int(cid) not in ranked
    ]

    due_rows: list[tuple[int, float, int]] = list(
        zip(
            (int(c) for c in due.card_ids),
            (float(r) for r in due.predicted_recall),
            (int(i) for i in due.suggested_interval_days),
        )
    )
    # New cards: recall 0.0 (weakest possible), no scheduled interval yet.
    new_rows: list[tuple[int, float, int]] = [(cid, 0.0, 0) for cid in new_cids]

    if fetch_limit:
        limit = int(fetch_limit)
        # New cards all share recall 0.0, so a naive weakest-first cut would let
        # a new-card backlog crowd genuinely-weak DUE cards out of the capped
        # view. Reserve at least half the slots for due cards; new cards take
        # every slot the due cards leave unused.
        due_take = min(len(due_rows), max(limit // 2, limit - len(new_rows)))
        merged = due_rows[:due_take] + new_rows[: limit - due_take]
    else:
        merged = due_rows + new_rows
    # Weakest predicted exam-day recall first; ties broken by ascending card id.
    merged.sort(key=lambda row: (row[1], row[0]))

    return cfa_deadline.DeadlineRetention(
        card_ids=[c for c, _, _ in merged],
        predicted_recall=[r for _, r, _ in merged],
        suggested_interval_days=[i for _, _, i in merged],
        used_rpc=due.used_rpc,
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


def _py_memory_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> MemoryScore:
    """Pure-Python reference implementation of the memory score.

    This is the canonical algorithm. The public :func:`memory_score` delegates
    to the shared Rust ``ComputeCfaScores`` engine (so desktop and mobile read
    identical numbers) and only falls back to this when the backend predates the
    RPC. Kept, too, as the parity reference verified in the test-suite.

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
    topic_prefixes = readiness_topic_prefixes(weights)

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


def _py_performance_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> PerformanceScore:
    """Pure-Python reference for the performance score (see :func:`_py_memory_score`).

    Estimate P(correct on a new question) from first-exposure accuracy.

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


def _py_readiness_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> ReadinessScore:
    """Pure-Python reference for the readiness score (see :func:`_py_memory_score`).

    Combine memory + performance + coverage into a wide, uncalibrated P(pass).
    Abstains (give-up rule) whenever either input score abstains — a readiness
    number is only as trustworthy as the two scores beneath it."""
    now_ts = now_ts if now_ts is not None else int(time.time())
    computed_at = datetime.fromtimestamp(now_ts).isoformat(timespec="seconds")

    mem = _py_memory_score(col, deck_id=deck_id, now_ts=now_ts)
    perf = _py_performance_score(col, deck_id=deck_id, now_ts=now_ts)

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


# =============================================================================
# F4 — Bayesian readiness: a number from the first review, no give-up wall
# =============================================================================
#
# The Feature-6 scores above abstain ("not enough data") until a hard evidence
# threshold is met. F4 replaces that wall with an *honest uncertainty band*:
#
#   1. SM-2 fallback — when FSRS retrievability R is NULL (SM-2-scheduled cards,
#      or FSRS not yet run), estimate per-card recall from the card's own review
#      history via a forgetting curve, so a recall number appears from the very
#      first review instead of "no data".
#
#   2. Bayesian CI — model each topic's correctness as a Beta-Bernoulli. With no
#      reviews the posterior is the uniform prior Beta(1,1) (mean 0.5, maximal
#      variance), so the exam-weighted accuracy band spans almost the whole exam.
#      As reviews accrue the posterior concentrates and the 95% band NARROWS.
#      Uncovered topics keep their wide prior, so the band stays honest about
#      syllabus you have not touched — no abstention, just wide uncertainty.
#
#   3. Explicit call — a pass/fail verdict with a probability computed against
#      the ~65% MPS proxy: P(exam accuracy >= MPS) under the aggregate posterior.
#      The standing "not validated against real exam data" caveat still applies.

# Beta prior for a topic with no evidence: uniform over [0, 1].
_PRIOR_A = 1.0
_PRIOR_B = 1.0
# Two-sided z for the 95% credible band.
_BAND_Z = 1.959963984540054


def estimate_recall(
    r: Optional[float],
    ivl_days: Optional[float],
    elapsed_days: Optional[float],
    successes: int,
    total: int,
) -> Optional[float]:
    """Per-card recall probability, with an SM-2 fallback when FSRS R is NULL.

    When ``r`` (FSRS retrievability) is available it is authoritative and used
    verbatim. When it is NULL — the SM-2 "no data" bug — we estimate recall from
    the card's own review history: an SM-2-style forgetting curve
    ``0.9 ** (elapsed / interval)`` (SM-2 targets ~90% retention at the scheduled
    interval) blended equally with the card's empirical success rate, so a
    chronically-lapsing card is not credited full recall. Returns None only when
    there is genuinely no history (never reviewed and no FSRS state)."""
    if r is not None:
        return max(0.0, min(1.0, float(r)))
    if total <= 0:
        return None
    ivl = max(1.0, float(ivl_days or 1))
    elapsed = max(0.0, float(elapsed_days or 0.0))
    curve = 0.9 ** (elapsed / ivl)
    empirical = successes / total
    return max(0.0, min(1.0, 0.5 * curve + 0.5 * empirical))


def _beta_posterior(successes: int, failures: int) -> tuple[float, float]:
    """Beta posterior (a, b) from a uniform prior updated with observed data."""
    return _PRIOR_A + successes, _PRIOR_B + failures


def _beta_mean_var(a: float, b: float) -> tuple[float, float]:
    """Mean and variance of Beta(a, b)."""
    n = a + b
    mean = a / n
    var = (a * b) / (n * n * (n + 1.0))
    return mean, var


def _norm_cdf(x: float) -> float:
    """Standard-normal CDF (via erf), used for the pass/fail probability."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class TopicPosterior:
    topic: str
    weight: float
    successes: int
    failures: int
    # Beta posterior mean correctness and its 95% credible interval.
    mean: float
    ci_low: float
    ci_high: float
    # Recall (FSRS R, or SM-2 fallback); None only with no history at all.
    recall: Optional[float]
    covered: bool


@dataclass
class BayesianReadiness:
    # Estimated exam accuracy (exam-weighted) as a point + 95% credible band.
    accuracy: float
    ci_low: float
    ci_high: float
    # Explicit pass/fail call against the MPS proxy.
    call: str  # "likely pass" | "likely fail"
    call_prob: float  # probability supporting the call (>= 0.5)
    p_pass: float  # P(exam accuracy >= MPS) under the aggregate posterior
    mps: float
    # Exam-weighted recall (incl. SM-2 fallback); None only with zero history.
    recall: Optional[float]
    # Standing honesty caveat, always present.
    label: str
    # Evidence: first-exposure trials feeding the posterior (band width shrinks
    # as these grow — never abstains).
    first_exposures: int
    topics_total: int
    topics_covered: int
    computed_at: str
    topics: list[TopicPosterior] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _py_bayesian_readiness(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> BayesianReadiness:
    """Pure-Python reference for the Bayesian readiness (see :func:`_py_memory_score`).

    Exam readiness as a Bayesian band + an explicit pass/fail call.

    Unlike :func:`readiness_score`, this NEVER abstains: with little evidence the
    95% credible band on estimated exam accuracy is very wide (the topics sit at
    their uniform priors), and it narrows honestly as graded reviews accrue. Per
    card, recall uses FSRS R when present and an SM-2 fallback otherwise so a
    number appears from the first review."""
    now_ts = now_ts if now_ts is not None else int(time.time())
    computed_at = datetime.fromtimestamp(now_ts).isoformat(timespec="seconds")

    if deck_id is not None:
        did_list = col.decks.deck_and_child_ids(DeckId(int(deck_id)))
        deck_filter = "c.did in (%s)" % ",".join(str(int(d)) for d in did_list)
    else:
        deck_filter = "1"

    today = col.sched.today
    next_day_at = col.sched.day_cutoff

    # Per card: retrievability (NULL when no FSRS state), interval, tags.
    rows: list[Any] = col.db.all(
        f"""
        select c.id, n.tags,
          extract_fsrs_retrievability(
            c.data,
            case when c.odue != 0 then c.odue else c.due end,
            c.ivl, ?, ?, ?),
          c.ivl
        from cards c join notes n on c.nid = n.id
        where {deck_filter}
        """,
        today,
        next_day_at,
        now_ts,
    )

    # Per card: graded-review success/total counts and last-review timestamp
    # (drive the SM-2 recall fallback), plus the ease of the FIRST graded review
    # (the exam-like Bernoulli trial that feeds the correctness posterior).
    stats: dict[int, tuple[int, int, int, Optional[int]]] = {}
    for cid, total, succ, last_ms, first_ease in col.db.all(
        f"""
        select c.id, count(*),
          sum(case when r.ease >= {_CORRECT_EASE} then 1 else 0 end),
          max(r.id),
          (select r2.ease from revlog r2
             where r2.cid = c.id and r2.ease > 0 order by r2.id limit 1)
        from revlog r join cards c on r.cid = c.id
        where {deck_filter} and r.ease > 0
        group by c.id
        """
    ):
        stats[int(cid)] = (
            int(total),
            int(succ or 0),
            int(last_ms or 0),
            int(first_ease) if first_ease is not None else None,
        )

    cfg = get_exam_config(col) or {}
    weights: dict[str, float] = cfg.get("topic_weights", {})
    topic_prefixes = readiness_topic_prefixes(weights)

    # Group per-topic correctness counts and recall estimates.
    per_succ: dict[str, int] = {t: 0 for t in topic_prefixes}
    per_fail: dict[str, int] = {t: 0 for t in topic_prefixes}
    per_recall: dict[str, list[float]] = {t: [] for t in topic_prefixes}
    for cid, tags, r, ivl in rows:
        topic = _topic_of(tags or "", topic_prefixes)
        if topic is None:
            continue
        total, succ, last_ms, first_ease = stats.get(int(cid), (0, 0, 0, None))
        # Correctness posterior: one first-exposure Bernoulli trial per card.
        if first_ease is not None:
            if first_ease >= _CORRECT_EASE:
                per_succ[topic] += 1
            else:
                per_fail[topic] += 1
        elapsed = (now_ts - last_ms / 1000.0) / 86_400.0 if last_ms else 0.0
        rec = estimate_recall(r, ivl, elapsed, succ, total)
        if rec is not None:
            per_recall[topic].append(rec)

    z = _BAND_Z
    topics: list[TopicPosterior] = []
    for topic in topic_prefixes:
        s, f = per_succ[topic], per_fail[topic]
        a, b = _beta_posterior(s, f)
        mean, var = _beta_mean_var(a, b)
        std = math.sqrt(var)
        recs = per_recall[topic]
        topics.append(
            TopicPosterior(
                topic=topic,
                weight=float(weights.get(topic, 0.0)),
                successes=s,
                failures=f,
                mean=mean,
                ci_low=max(0.0, mean - z * std),
                ci_high=min(1.0, mean + z * std),
                recall=(statistics.fmean(recs) if recs else None),
                covered=(s + f) > 0,
            )
        )

    # Exam-weighted aggregate. Normalise weights; fall back to equal weighting
    # when no exam weights are configured (all-zero).
    raw_w = [max(0.0, t.weight) for t in topics]
    if sum(raw_w) <= 0:
        raw_w = [1.0] * len(topics)
    total_w = sum(raw_w) or 1.0
    norm_w = [w / total_w for w in raw_w]

    mu = 0.0
    var_agg = 0.0
    rec_num = 0.0
    rec_den = 0.0
    for t, w in zip(topics, norm_w):
        a, b = _beta_posterior(t.successes, t.failures)
        m, v = _beta_mean_var(a, b)
        mu += w * m
        var_agg += w * w * v
        if t.recall is not None:
            rec_num += w * t.recall
            rec_den += w
    std_agg = math.sqrt(var_agg)

    accuracy = max(0.0, min(1.0, mu))
    ci_low = max(0.0, mu - z * std_agg)
    ci_high = min(1.0, mu + z * std_agg)

    # P(exam accuracy >= MPS) under the normal approximation to the aggregate.
    if std_agg > 0:
        p_pass = 1.0 - _norm_cdf((_MPS - mu) / std_agg)
    else:
        p_pass = 1.0 if mu >= _MPS else 0.0
    p_pass = max(0.0, min(1.0, p_pass))
    if p_pass >= 0.5:
        call, call_prob = "likely pass", p_pass
    else:
        call, call_prob = "likely fail", 1.0 - p_pass

    first_exposures = sum(t.successes + t.failures for t in topics)
    return BayesianReadiness(
        accuracy=accuracy,
        ci_low=ci_low,
        ci_high=ci_high,
        call=call,
        call_prob=call_prob,
        p_pass=p_pass,
        mps=_MPS,
        recall=(rec_num / rec_den if rec_den > 0 else None),
        label=READINESS_LABEL,
        first_exposures=first_exposures,
        topics_total=len(topics),
        topics_covered=sum(1 for t in topics if t.covered),
        computed_at=computed_at,
        topics=topics,
    )


# =============================================================================
# Thin wrappers over the shared Rust engine (ComputeCfaScores RPC)
# =============================================================================
#
# The four public score functions delegate to the read-only Rust
# ``ComputeCfaScores`` RPC — the SAME engine the AnkiDroid client calls — so the
# numbers are computed in exactly one place and desktop == mobile by
# construction. The Rust port is a faithful mirror of the ``_py_*`` references
# above (verified field-by-field to 1e-9 in the test-suite) and additionally
# de-duplicates graded reviews to at most one per (card, day), so an offline
# dual-device round-trip cannot double-count. If the loaded backend predates the
# RPC (an older ``_rsbridge``), the wrappers transparently fall back to the
# pure-Python reference, so scores never disappear.


def _pb_opt(msg: Any, name: str) -> Any:
    """Read a proto3 ``optional`` field, returning None when it is unset.

    Polymorphic over the field type (the ``double`` score fields and the
    ``string`` ``last_review_at``), so the return type is ``Any``."""
    return getattr(msg, name) if msg.HasField(name) else None


def _memory_from_pb(pb: Any) -> MemoryScore:
    return MemoryScore(
        abstain=pb.abstain,
        reason=pb.reason,
        point=_pb_opt(pb, "point"),
        range_low=_pb_opt(pb, "range_low"),
        range_high=_pb_opt(pb, "range_high"),
        coverage_pct=pb.coverage_pct,
        topics_total=pb.topics_total,
        topics_covered=pb.topics_covered,
        graded_reviews=pb.graded_reviews,
        last_review_at=_pb_opt(pb, "last_review_at"),
        computed_at=pb.computed_at,
        topics=[
            TopicScore(
                topic=t.topic,
                weight=t.weight,
                reviewed_cards=t.reviewed_cards,
                graded_reviews=t.graded_reviews,
                avg_r=_pb_opt(t, "avg_r"),
                r_low=_pb_opt(t, "r_low"),
                r_high=_pb_opt(t, "r_high"),
                covered=t.covered,
            )
            for t in pb.topics
        ],
    )


def _performance_from_pb(pb: Any) -> PerformanceScore:
    return PerformanceScore(
        abstain=pb.abstain,
        reason=pb.reason,
        point=_pb_opt(pb, "point"),
        range_low=_pb_opt(pb, "range_low"),
        range_high=_pb_opt(pb, "range_high"),
        first_exposures=pb.first_exposures,
        correct=pb.correct,
        computed_at=pb.computed_at,
    )


def _readiness_from_pb(pb: Any) -> ReadinessScore:
    return ReadinessScore(
        abstain=pb.abstain,
        reason=pb.reason,
        point=_pb_opt(pb, "point"),
        range_low=_pb_opt(pb, "range_low"),
        range_high=_pb_opt(pb, "range_high"),
        label=pb.label,
        memory_point=_pb_opt(pb, "memory_point"),
        performance_point=_pb_opt(pb, "performance_point"),
        coverage_pct=pb.coverage_pct,
        computed_at=pb.computed_at,
    )


def _bayesian_from_pb(pb: Any) -> BayesianReadiness:
    return BayesianReadiness(
        accuracy=pb.accuracy,
        ci_low=pb.ci_low,
        ci_high=pb.ci_high,
        call=pb.call,
        call_prob=pb.call_prob,
        p_pass=pb.p_pass,
        mps=pb.mps,
        recall=_pb_opt(pb, "recall"),
        label=pb.label,
        first_exposures=pb.first_exposures,
        topics_total=pb.topics_total,
        topics_covered=pb.topics_covered,
        computed_at=pb.computed_at,
        topics=[
            TopicPosterior(
                topic=t.topic,
                weight=t.weight,
                successes=t.successes,
                failures=t.failures,
                mean=t.mean,
                ci_low=t.ci_low,
                ci_high=t.ci_high,
                recall=_pb_opt(t, "recall"),
                covered=t.covered,
            )
            for t in pb.topics
        ],
    )


def _compute_scores_via_rpc(
    col: anki.collection.Collection,
    deck_id: Optional[DeckId | int],
    now_ts: Optional[int],
) -> Any:
    """Call the shared Rust engine once, returning the full proto response.

    Raises ``AttributeError`` when the loaded backend has no ``compute_cfa_scores``
    method (an older ``_rsbridge``), which the callers use to fall back."""
    return col._backend.compute_cfa_scores(
        deck_id=int(deck_id) if deck_id is not None else 0,
        whole_collection=deck_id is None,
        now=int(now_ts) if now_ts is not None else 0,
    )


def memory_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> MemoryScore:
    """Honest, give-up-aware memory score for a deck (or the whole collection).

    Delegates to the shared Rust ``ComputeCfaScores`` engine; see
    :func:`_py_memory_score` for the algorithm."""
    try:
        return _memory_from_pb(_compute_scores_via_rpc(col, deck_id, now_ts).memory)
    except AttributeError:
        return _py_memory_score(col, deck_id=deck_id, now_ts=now_ts)


def performance_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> PerformanceScore:
    """P(correct on a new question) from first-exposure accuracy (Wilson 95%).

    Delegates to the shared Rust engine; see :func:`_py_performance_score`."""
    try:
        return _performance_from_pb(
            _compute_scores_via_rpc(col, deck_id, now_ts).performance
        )
    except AttributeError:
        return _py_performance_score(col, deck_id=deck_id, now_ts=now_ts)


def readiness_score(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> ReadinessScore:
    """Wide, uncalibrated P(pass) fusing memory + performance + coverage.

    Delegates to the shared Rust engine; see :func:`_py_readiness_score`."""
    try:
        return _readiness_from_pb(
            _compute_scores_via_rpc(col, deck_id, now_ts).readiness
        )
    except AttributeError:
        return _py_readiness_score(col, deck_id=deck_id, now_ts=now_ts)


def bayesian_readiness(
    col: anki.collection.Collection,
    *,
    deck_id: Optional[DeckId | int] = None,
    now_ts: Optional[int] = None,
) -> BayesianReadiness:
    """Bayesian readiness band + explicit pass/fail call (never abstains).

    Delegates to the shared Rust engine; see :func:`_py_bayesian_readiness`."""
    try:
        return _bayesian_from_pb(_compute_scores_via_rpc(col, deck_id, now_ts).bayesian)
    except AttributeError:
        return _py_bayesian_readiness(col, deck_id=deck_id, now_ts=now_ts)
