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


# ------------------------------------------------------------------- multi-span highlight grading
#
# F1 one-passage redesign. Instead of two side-by-side vignettes with ONE decisive phrase, the
# learner reads ONE passage, calls it Ethical/Unethical, and highlights EVERY evidence span that
# supports that verdict. The evidence may be SEVERAL NON-CONTIGUOUS spans, so grading is by
# per-span coverage rather than a single contiguous overlap.
#
# find_gold_spans() / grade_spans() are the deterministic AI-off fallback for F2's semantic grader.
# They are mirrored CHARACTER-FOR-CHARACTER by the passage card template JS (templates/
# passage_front.html, between the CFA-SPAN-SHARED markers) and by tests/js/passage_logic.js, so the
# grade strings are byte-identical on desktop Anki and AnkiDroid. tests/test_passages.py enforces
# the copy match and the Python<->JS behavioural agreement. Keep the three copies in sync.

ETHICAL = "ethical"
UNETHICAL = "unethical"
VERDICTS = (ETHICAL, UNETHICAL)

# Per-span width allowance. The total-selection cap for a multi-span attempt scales with the number
# of gold spans, since the learner makes one sub-selection per span: cap = |gold| + slack * n_spans.
SPAN_CAP_SLACK = 4


def find_gold_spans(passage: str, phrases: Sequence[str]) -> list[list[int]]:
    """Resolve each verbatim gold ``phrase`` to its contiguous token-index run inside ``passage``.

    Returns one index run per phrase, preserving order (an empty run if a phrase is not locatable).
    Each run is contiguous, but the runs are generally NON-CONTIGUOUS with one another. Identical
    algorithm to the passage template JS ``cfaFindGoldSpans``.
    """
    return [find_gold_indices(passage, p) for p in phrases]


def span_cap(gold_token_count: int, n_spans: int) -> int:
    """Upper bound on |SELECTION| that still counts as CORRECT: ``gold + SPAN_CAP_SLACK * n_spans``."""
    return gold_token_count + SPAN_CAP_SLACK * max(1, n_spans)


def grade_spans(
    selection_indices: Sequence[int],
    gold_spans: Sequence[Sequence[int]],
    cap: int | None = None,
) -> dict:
    """Grade a multi-span highlight by per-span coverage. Returns a result dict with a ``grade``.

    A gold span is FOUND when every one of its tokens is in the learner's selection. Grades:

    - ``"correct"``  -- EVERY gold span is found AND ``|selection| <= cap`` (no runaway width).
    - ``"somewhat"`` -- every gold span is found BUT ``|selection| > cap`` (right regions, over-wide).
    - ``"partial"``  -- at least one but NOT all gold spans are found.
    - ``"wrong"``    -- no gold span is found, or the selection is empty.

    ``cap`` defaults to ``span_cap(total_gold_tokens, n_spans)``. Only ``"correct"`` counts as a
    fully-correct highlight in ``grade_passage_attempt``.
    """
    selection = set(selection_indices)
    per_span = []
    all_gold: set[int] = set()
    found = 0
    for span in gold_spans:
        s = set(span)
        all_gold |= s
        covered = bool(s) and s.issubset(selection)
        per_span.append(covered)
        if covered:
            found += 1
    total = len(gold_spans)
    if cap is None:
        cap = span_cap(len(all_gold), total)
    width_ok = len(selection) <= cap
    if not selection or found == 0:
        grade = "wrong"
    elif found < total:
        grade = "partial"
    elif not width_ok:
        grade = "somewhat"
    else:
        grade = "correct"
    return {
        "grade": grade,
        "found": found,
        "total": total,
        "per_span": per_span,
        "width_ok": width_ok,
        "cap": cap,
    }


# --- Item 2: deterministic partial-credit tolerance (the AI-off / mobile grade) ------------------
#
# grade_spans above is exact but brittle: it credits a gold span only when EVERY one of its tokens is
# selected, so a materially-correct highlight with different boundaries (e.g. "unreleased quarterly
# earnings" for the gold "exact unreleased quarterly earnings figure") scores a flat "wrong".
# span_tier / grade_spans_tolerant add DETERMINISTIC tolerance (no network, no LLM): a span is "full"
# when every gold token is covered (a superset still counts), "near" when the selection overlaps at
# least half the gold tokens (right idea, boundaries off), else "none"; grade_spans_tolerant then
# awards partial-credit tiers. This mirrors the desktop F2 grader's tolerance while staying offline
# and deterministic, and is mirrored CHARACTER-FOR-CHARACTER by cfaSpanTier / cfaGradeSpansTolerant
# in the passage card template JS and tests/js/passage_logic.js. tests/test_passages.py enforces the
# copy match and the Python<->JS behavioural agreement. Keep the three copies in sync.


def span_tier(selection: set, span: Sequence[int]) -> str:
    """Tolerant per-span match tier: ``"full"`` | ``"near"`` | ``"none"``.

    ``"full"`` = every gold token in the span is selected (a superset still counts). ``"near"`` = the
    selection overlaps at least half the span's gold tokens (right idea, boundaries off). Otherwise
    ``"none"``. Identical logic to the template JS ``cfaSpanTier``.
    """
    s = set(span)
    if not s:
        return "none"
    inter = len(s & selection)
    if inter == len(s):
        return "full"
    if inter > 0 and inter * 2 >= len(s):
        return "near"
    return "none"


def grade_spans_tolerant(
    selection_indices: Sequence[int],
    gold_spans: Sequence[Sequence[int]],
    cap: int | None = None,
) -> dict:
    """Grade a multi-span highlight with partial-credit tolerance (deterministic AI-off/mobile grade).

    Like :func:`grade_spans` but a gold span counts when the learner's selection materially overlaps
    it, not only when it is fully covered. Grades:

    - ``"correct"``  -- every gold span is FULLY covered AND ``|selection| <= cap``.
    - ``"somewhat"`` -- every gold span is matched (full or near) but at least one is only near, OR
      all are full but ``|selection| > cap`` (right regions, imperfect boundaries / over-wide).
    - ``"partial"``  -- at least one but NOT all gold spans are matched (full or near).
    - ``"wrong"``    -- no gold span is matched, or the selection is empty.

    ``per_span`` is a list of tier strings (``"full"`` / ``"near"`` / ``"none"``); ``found`` counts
    FULL matches and ``near`` counts near matches. Only ``"correct"`` counts as a fully-correct
    highlight. Identical logic to the template JS ``cfaGradeSpansTolerant``.
    """
    selection = set(selection_indices)
    per_span: list[str] = []
    all_gold: set[int] = set()
    full = 0
    near = 0
    for span in gold_spans:
        all_gold |= set(span)
        tier = span_tier(selection, span)
        per_span.append(tier)
        if tier == "full":
            full += 1
        elif tier == "near":
            near += 1
    total = len(gold_spans)
    matched = full + near
    if cap is None:
        cap = span_cap(len(all_gold), total)
    width_ok = len(selection) <= cap
    if not selection or matched == 0:
        grade = "wrong"
    elif matched < total:
        grade = "partial"
    elif full == total and width_ok:
        grade = "correct"
    else:
        grade = "somewhat"
    return {
        "grade": grade,
        "found": full,
        "near": near,
        "matched": matched,
        "total": total,
        "per_span": per_span,
        "width_ok": width_ok,
        "cap": cap,
    }


@dataclass(frozen=True)
class PassageAttempt:
    """One learner attempt at a single one-passage item, with the answer key to grade against.

    ``judged_verdict`` is the learner's Ethical/Unethical call, ``answer_verdict`` the correct one.
    ``selection_indices`` are ALL word indices the learner highlighted across every span they marked
    (union, order-independent); ``gold_spans`` are the authored evidence spans' index runs.
    """

    judged_verdict: str
    answer_verdict: str
    selection_indices: Sequence[int]
    gold_spans: Sequence[Sequence[int]]
    cap: int | None = None


def grade_passage_attempt(attempt: PassageAttempt) -> dict:
    """Deterministically grade one one-passage attempt (verdict + multi-span evidence highlight).

    ``correct`` is True only when the verdict is right AND the multi-span highlight grades fully
    ``"correct"`` (every gold span found, within the width cap). This is the AI-off fallback grade.
    """
    verdict_correct = attempt.judged_verdict == attempt.answer_verdict
    spans = grade_spans(attempt.selection_indices, attempt.gold_spans, attempt.cap)
    highlight_correct = spans["grade"] == "correct"
    correct = verdict_correct and highlight_correct
    return {
        "verdict_correct": verdict_correct,
        "highlight": spans["grade"],
        "spans": spans,
        "highlight_correct": highlight_correct,
        "correct": correct,
    }


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
