"""Tests for the CFA held-out eval harness (Feature 7).

Stdlib only — no built pylib required. Exercises three things:
  * the eval runs and returns well-formed metrics in valid ranges;
  * the eval is deterministic for a fixed seed and varies with the seed;
  * the leakage check reports the held-out set clean against the deck.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL_DIR = os.path.dirname(HERE)
sys.path.insert(0, EVAL_DIR)

import leakage_check  # noqa: E402
import run_eval  # noqa: E402


def test_heldout_shape():
    items = run_eval.load_heldout()
    assert len(items) == 30, "expected 30 held-out concepts"
    ids = {it["concept_id"] for it in items}
    assert len(ids) == 30, "concept ids must be unique"
    for it in items:
        # Each concept carries two genuinely different reworded questions.
        assert it["question_a"] and it["question_b"]
        assert it["question_a"] != it["question_b"]
        assert 0.0 <= float(it["difficulty"]) <= 1.0
        assert it["los_tag"].startswith("los::")


def test_eval_runs_and_ranges():
    m = run_eval.run(seed=0, learners=100)
    assert m["concepts"] == 30
    assert m["questions"] == 60
    assert m["predictions"] == 60 * 100
    assert 0.0 <= m["accuracy"] <= 1.0
    assert 0.0 <= m["auc"] <= 1.0 and not math.isnan(m["auc"])
    assert 0.0 <= m["ece"] <= 1.0
    # The model has real signal and is reasonably calibrated on the sim.
    assert m["auc"] > 0.6
    assert m["ece"] < 0.15


def test_paraphrase_stability():
    m = run_eval.run(seed=0, learners=100)
    # Two paraphrases of one concept should get near-identical predictions
    # (mean within ~5 percentage points, worst case within ~15).
    assert m["paraphrase_gap_mean"] < 0.06
    assert m["paraphrase_gap_max"] < 0.15


def test_deterministic_seed():
    a = run_eval.run(seed=7, learners=100)
    b = run_eval.run(seed=7, learners=100)
    assert a == b, "same seed must reproduce identical metrics"
    c = run_eval.run(seed=8, learners=100)
    assert c["accuracy"] != a["accuracy"] or c["ece"] != a["ece"], (
        "different seed should change the sampled outcomes"
    )


def test_auc_helper_perfect_and_random():
    # Perfectly separating scores -> AUC 1.0.
    assert run_eval._auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == 1.0
    # Inverted -> AUC 0.0.
    assert run_eval._auc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]) == 0.0


def test_leakage_clean():
    violations = leakage_check.check(verbose=False)
    assert violations == [], f"held-out set leaks into deck: {violations}"
