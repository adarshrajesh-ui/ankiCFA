# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Deterministic scoring + per-cluster discrimination aggregation for CFA Ethics Minimal-Pairs.

This module is PURE: it has NO dependency on the ``anki`` package. It consumes plain
value objects (``PairAttempt`` / ``AttemptRecord``) so the scoring rule and the per-cluster
aggregation can be unit-tested with synthetic fixtures, independent of any Anki build.
(This mirrors the project PRD's scoring contract: the scorer consumes review records and
never depends on Anki building.)

Two responsibilities:

1. ``grade_attempt`` -- the deterministic scoring rule. A pair attempt is "correct" ONLY if
   BOTH conform/violate judgments are right AND the decisive fact is named correctly.
2. ``discrimination_by_cluster`` -- the honest per-cluster "discrimination score": the
   percentage of the last N attempts that were fully correct, per confusable-Standard cluster,
   abstaining ("not enough data") below a minimum attempt count.

The discrimination score is intentionally SEPARATE from Anki's FSRS memory statistics: it
measures whether the learner can tell near-identical cases apart, not how well they remember.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

CONFORM = "conform"
VIOLATE = "violate"
JUDGMENTS = (CONFORM, VIOLATE)

# Honesty thresholds (documented in README.md). Below MIN_ATTEMPTS in a cluster we abstain and
# report "not enough data" rather than a misleadingly precise number. The score is computed over
# the most recent WINDOW attempts so it reflects current discrimination, not ancient history.
DEFAULT_MIN_ATTEMPTS = 5
DEFAULT_WINDOW = 20

# 95% two-sided normal quantile, used for the Wilson score interval.
_Z_95 = 1.959963984540054


def _norm(text: str) -> str:
    """Whitespace/case-insensitive normalization for comparing MCQ option text."""
    return " ".join((text or "").split()).casefold()


@dataclass(frozen=True)
class PairAttempt:
    """One learner attempt at a single minimal-pair, with the correct answers to grade against.

    ``judged_a``/``judged_b`` are the learner's conform/violate calls for each vignette.
    ``chosen_fact`` is the MCQ option text the learner selected as the decisive difference.
    """

    judged_a: str
    judged_b: str
    chosen_fact: str
    answer_a: str
    answer_b: str
    decisive_fact: str


def grade_attempt(attempt: PairAttempt) -> dict:
    """Deterministically grade one pair attempt.

    Returns a dict with the three sub-results and the overall ``correct`` flag. ``correct`` is
    True only when every sub-answer is right -- getting the two judgments right but naming the
    wrong decisive fact (or vice-versa) is NOT correct.
    """
    judgment_a_correct = attempt.judged_a == attempt.answer_a
    judgment_b_correct = attempt.judged_b == attempt.answer_b
    decisive_fact_correct = _norm(attempt.chosen_fact) == _norm(attempt.decisive_fact)
    correct = judgment_a_correct and judgment_b_correct and decisive_fact_correct
    return {
        "judgment_a_correct": judgment_a_correct,
        "judgment_b_correct": judgment_b_correct,
        "decisive_fact_correct": decisive_fact_correct,
        "correct": correct,
    }


@dataclass(frozen=True)
class AttemptRecord:
    """A recorded pair attempt used for aggregation.

    ``cluster`` is the confusable-Standard cluster id, ``correct`` the deterministic grade, and
    ``order`` a monotonically increasing key (e.g. a revlog id or millisecond timestamp) used to
    pick the most-recent attempts. Synthetic records are used in tests; real records come from the
    review log via ``ethics_revlog``.
    """

    cluster: str
    correct: bool
    order: int


def _wilson_interval(correct: int, n: int, z: float = _Z_95) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion, returned as percentages.

    Preferred over the naive normal interval because it is well-behaved for small n and near 0%/100%.
    """
    if n == 0:
        return (0.0, 0.0)
    phat = correct / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) + z * z / (4 * n)) / n)
    lo = max(0.0, (centre - margin) / denom)
    hi = min(1.0, (centre + margin) / denom)
    return (round(100.0 * lo, 1), round(100.0 * hi, 1))


def _confidence(n: int, min_attempts: int, window: int) -> str:
    if n < min_attempts:
        return "none"
    if n < window // 2:
        return "low"
    if n < window:
        return "medium"
    return "high"


def score_cluster(
    cluster: str,
    recent_correct: int,
    recent_n: int,
    total_attempts: int,
    min_attempts: int = DEFAULT_MIN_ATTEMPTS,
    window: int = DEFAULT_WINDOW,
) -> dict:
    """Build an honest score object for one cluster.

    The shape mirrors the PRD's score contract: a point estimate, an interval, a coverage figure,
    a confidence label, and an explicit ``abstain`` flag with a human reason.
    """
    abstain = recent_n < min_attempts
    point = None if abstain else round(100.0 * recent_correct / recent_n, 1)
    interval = None if abstain else _wilson_interval(recent_correct, recent_n)
    return {
        "cluster": cluster,
        "point": point,
        "range": interval,
        "attempts_in_window": recent_n,
        "correct_in_window": recent_correct,
        "total_attempts": total_attempts,
        "window": window,
        "min_attempts": min_attempts,
        "coverage_pct": round(100.0 * min(recent_n, window) / window, 1),
        "confidence": _confidence(recent_n, min_attempts, window),
        "abstain": abstain,
        "reason": "not enough data" if abstain else "ok",
    }


def discrimination_by_cluster(
    records: list[AttemptRecord],
    min_attempts: int = DEFAULT_MIN_ATTEMPTS,
    window: int = DEFAULT_WINDOW,
) -> dict[str, dict]:
    """Aggregate attempt records into a per-cluster discrimination score object.

    For each cluster, scores the most recent ``window`` attempts and abstains below ``min_attempts``.
    """
    by_cluster: dict[str, list[AttemptRecord]] = {}
    for r in records:
        by_cluster.setdefault(r.cluster, []).append(r)

    out: dict[str, dict] = {}
    for cluster, recs in by_cluster.items():
        recs_sorted = sorted(recs, key=lambda r: r.order)
        recent = recs_sorted[-window:]
        recent_correct = sum(1 for r in recent if r.correct)
        out[cluster] = score_cluster(
            cluster, recent_correct, len(recent), len(recs_sorted), min_attempts, window
        )
    return out
