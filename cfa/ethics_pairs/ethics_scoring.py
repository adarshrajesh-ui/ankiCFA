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
   BOTH conform/violate judgments are right AND the learner's in-vignette highlight of the decisive
   phrase is fully "correct" (see ``grade_highlight``; a "somewhat" highlight does NOT count).
2. ``discrimination_by_cluster`` -- the honest per-cluster "discrimination score": the
   percentage of the last N attempts that were fully correct, per confusable-Standard cluster,
   abstaining ("not enough data") below a minimum attempt count.

The discrimination score is intentionally SEPARATE from Anki's FSRS memory statistics: it
measures whether the learner can tell near-identical cases apart, not how well they remember.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
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


# ------------------------------------------------------------------- highlight grading
#
# The learner highlights the decisive phrase directly inside the vignette. Grading is by WORD-SPAN
# OVERLAP between the learner's contiguous SELECTION and the authored GOLD phrase.
#
# The single tunable that sets how much slack a learner gets is HIGHLIGHT_CAP_SLACK: a selection
# that contains every gold word counts as CORRECT as long as it is at most
# ``len(gold) + HIGHLIGHT_CAP_SLACK`` words long (the "cap"); if it contains every gold word but is
# longer than the cap it is SOMEWHAT (right region, too wide); anything else is WRONG.
#
# tokenize()/normalized_tokens()/find_gold_indices()/grade_highlight() are mirrored CHARACTER-FOR-
# CHARACTER by the card template JS (templates/front.html, between the CFA-HIGHLIGHT-SHARED markers)
# so gold indices and grades are byte-identical on desktop Anki and on AnkiDroid. Keep them in sync;
# tests/test_highlight.py enforces both the cross-language agreement and that the copies match.

# The one tunable constant governing the CORRECT/SOMEWHAT cap (cap = len(gold) + this).
HIGHLIGHT_CAP_SLACK = 5

# Punctuation stripped from BOTH ENDS of a token before comparison; interior punctuation such as
# the apostrophe in "client's" or the hyphen in "in-house" is preserved. Must match the JS set.
_STRIP_CHARS = ".,;:!?\"'()[]{}…-–—‘’“”"


def tokenize(text: str) -> list[str]:
    """Split ``text`` into word tokens on runs of whitespace (``None``/blank -> [])."""
    if text is None:
        return []
    return str(text).split()


def _strip_token(token: str) -> str:
    """Lowercase a token after stripping surrounding punctuation (interior punctuation kept)."""
    return token.strip(_STRIP_CHARS).lower()


def normalized_tokens(text: str) -> list[str]:
    """Tokenize ``text`` then normalize each token (lowercase + surrounding-punctuation strip)."""
    return [_strip_token(t) for t in tokenize(text)]


def find_gold_indices(vignette: str, gold: str) -> list[int]:
    """Locate ``gold`` inside ``vignette`` by matching normalized token runs.

    Returns the FIRST contiguous list of vignette token indices whose normalized forms equal
    ``gold``'s normalized tokens, or ``[]`` if not found. Identical algorithm to the template JS.
    """
    v = normalized_tokens(vignette)
    g = normalized_tokens(gold)
    if not g:
        return []
    for start in range(0, len(v) - len(g) + 1):
        if v[start : start + len(g)] == g:
            return list(range(start, start + len(g)))
    return []


def default_cap(gold_len: int) -> int:
    """Upper bound on |SELECTION| that still counts as CORRECT: ``gold_len + HIGHLIGHT_CAP_SLACK``."""
    return gold_len + HIGHLIGHT_CAP_SLACK


def grade_highlight(
    selection_indices: Sequence[int],
    gold_indices: Sequence[int],
    cap: int | None = None,
) -> str:
    """Grade a highlight by word-span overlap. Returns ``"correct"`` | ``"somewhat"`` | ``"wrong"``.

    - CORRECT: the selection contains EVERY gold word AND ``|selection| <= cap``.
    - SOMEWHAT: the selection contains EVERY gold word BUT ``|selection| > cap`` (right region, too wide).
    - WRONG: the selection is empty, or it misses at least one gold word.

    ``cap`` defaults to ``default_cap(len(gold_indices))`` == ``len(gold) + HIGHLIGHT_CAP_SLACK``.
    """
    selection = set(selection_indices)
    gold = set(gold_indices)
    if cap is None:
        cap = default_cap(len(gold))
    if not selection:
        return "wrong"
    if not gold.issubset(selection):
        return "wrong"
    return "correct" if len(selection) <= cap else "somewhat"


@dataclass(frozen=True)
class PairAttempt:
    """One learner attempt at a single minimal-pair, with the correct answers to grade against.

    ``judged_a``/``judged_b`` are the learner's conform/violate calls for each vignette.
    ``selection_case`` is the vignette the learner highlighted in ("A"/"B", or "" if nothing was
    highlighted) and ``selection_indices`` the contiguous word indices they highlighted there.
    ``decisive_case`` is the vignette that actually holds the decisive phrase and ``gold_indices``
    that phrase's word indices. A highlight only counts when it is made in ``decisive_case``.
    """

    judged_a: str
    judged_b: str
    answer_a: str
    answer_b: str
    selection_case: str
    selection_indices: Sequence[int]
    decisive_case: str
    gold_indices: Sequence[int]
    cap: int | None = None


def grade_attempt(attempt: PairAttempt) -> dict:
    """Deterministically grade one pair attempt.

    Returns the sub-results and the overall ``correct`` flag. ``correct`` is True only when BOTH
    conform/violate judgments are right AND the highlight is fully ``"correct"`` -- a ``"somewhat"``
    highlight (right region but too wide), a highlight in the wrong vignette, or no highlight at all
    does NOT count as fully correct.
    """
    judgment_a_correct = attempt.judged_a == attempt.answer_a
    judgment_b_correct = attempt.judged_b == attempt.answer_b
    # A selection only applies if it was made in the vignette that actually holds the gold phrase.
    effective_selection = (
        attempt.selection_indices
        if attempt.selection_case == attempt.decisive_case
        else ()
    )
    highlight = grade_highlight(effective_selection, attempt.gold_indices, attempt.cap)
    highlight_correct = highlight == "correct"
    correct = judgment_a_correct and judgment_b_correct and highlight_correct
    return {
        "judgment_a_correct": judgment_a_correct,
        "judgment_b_correct": judgment_b_correct,
        "highlight": highlight,
        "highlight_correct": highlight_correct,
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
