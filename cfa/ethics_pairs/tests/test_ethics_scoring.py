# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Pure unit tests for the deterministic scoring rule and per-cluster aggregation.

No ``anki`` dependency -- runs anywhere pytest can import ``ethics_scoring``.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ethics_scoring import (  # noqa: E402
    CONFORM,
    VIOLATE,
    AttemptRecord,
    PairAttempt,
    discrimination_by_cluster,
    grade_attempt,
)


def _attempt(judged_a, judged_b, chosen_fact, *, decisive="THE decisive fact"):
    """Build a PairAttempt whose correct answers are A=violate, B=conform, decisive=`decisive`."""
    return PairAttempt(
        judged_a=judged_a,
        judged_b=judged_b,
        chosen_fact=chosen_fact,
        answer_a=VIOLATE,
        answer_b=CONFORM,
        decisive_fact=decisive,
    )


# ---------------------------------------------------------------- scoring rule


def test_fully_correct_requires_all_three():
    res = grade_attempt(_attempt(VIOLATE, CONFORM, "THE decisive fact"))
    assert res["correct"] is True
    assert (
        res["judgment_a_correct"]
        and res["judgment_b_correct"]
        and res["decisive_fact_correct"]
    )


def test_wrong_judgment_a_fails_even_if_rest_right():
    res = grade_attempt(_attempt(CONFORM, CONFORM, "THE decisive fact"))
    assert res["judgment_a_correct"] is False
    assert res["correct"] is False


def test_wrong_judgment_b_fails_even_if_rest_right():
    res = grade_attempt(_attempt(VIOLATE, VIOLATE, "THE decisive fact"))
    assert res["judgment_b_correct"] is False
    assert res["correct"] is False


def test_wrong_decisive_fact_fails_even_if_both_judgments_right():
    # This is the crucial rule: naming the wrong decisive fact is NOT correct.
    res = grade_attempt(_attempt(VIOLATE, CONFORM, "a plausible but wrong distractor"))
    assert res["judgment_a_correct"] and res["judgment_b_correct"]
    assert res["decisive_fact_correct"] is False
    assert res["correct"] is False


def test_decisive_fact_match_is_whitespace_and_case_insensitive():
    res = grade_attempt(_attempt(VIOLATE, CONFORM, "  the  DECISIVE   Fact  "))
    assert res["decisive_fact_correct"] is True
    assert res["correct"] is True


# --------------------------------------------------------- cluster aggregation


def _records(cluster, results, start=1):
    """results is a list of bools; order increases so the last ones are the most recent."""
    return [
        AttemptRecord(cluster=cluster, correct=c, order=start + i)
        for i, c in enumerate(results)
    ]


def test_abstains_below_minimum_attempts():
    recs = _records("c1", [True, True, True, True])  # 4 < default min 5
    out = discrimination_by_cluster(recs)
    s = out["c1"]
    assert s["abstain"] is True
    assert s["point"] is None
    assert s["range"] is None
    assert s["reason"] == "not enough data"
    assert s["confidence"] == "none"
    assert s["total_attempts"] == 4


def test_scores_at_minimum_attempts():
    recs = _records("c1", [True, True, False, True, True])  # 4/5 correct
    s = discrimination_by_cluster(recs)["c1"]
    assert s["abstain"] is False
    assert s["point"] == 80.0
    assert s["attempts_in_window"] == 5
    assert s["correct_in_window"] == 4
    lo, hi = s["range"]
    assert 0.0 <= lo <= 80.0 <= hi <= 100.0  # interval brackets the point estimate


def test_window_keeps_only_most_recent():
    # 25 attempts: first 5 all wrong, most recent 20 all correct -> window should show 100%.
    recs = _records("c1", [False] * 5 + [True] * 20)
    s = discrimination_by_cluster(recs, min_attempts=5, window=20)["c1"]
    assert s["attempts_in_window"] == 20
    assert s["correct_in_window"] == 20
    assert s["point"] == 100.0
    assert s["total_attempts"] == 25
    assert s["confidence"] == "high"


def test_order_field_drives_recency_not_list_position():
    # Provide records out of order; the two lowest-order (oldest) are wrong.
    recs = [
        AttemptRecord("c1", True, 100),
        AttemptRecord("c1", False, 1),
        AttemptRecord("c1", True, 50),
        AttemptRecord("c1", False, 2),
        AttemptRecord("c1", True, 99),
    ]
    s = discrimination_by_cluster(recs, min_attempts=3, window=3)["c1"]
    # window=3 -> keep orders {50,99,100} which are all correct.
    assert s["attempts_in_window"] == 3
    assert s["correct_in_window"] == 3
    assert s["point"] == 100.0


def test_clusters_are_independent():
    recs = _records("mnpi", [True] * 6) + _records("priority", [False] * 6, start=100)
    out = discrimination_by_cluster(recs)
    assert out["mnpi"]["point"] == 100.0
    assert out["priority"]["point"] == 0.0
    assert set(out) == {"mnpi", "priority"}
