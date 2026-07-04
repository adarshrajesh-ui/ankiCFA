# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A4 tests — performance-model accuracy on held-out exam-style questions.

Stdlib only; no built pylib. Covers determinism, the no-leakage concept split,
that the trained model beats the majority baseline, learned-weight signs, the
stated gate, and the SIMULATED labelling contract.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL_DIR = os.path.dirname(HERE)
sys.path.insert(0, EVAL_DIR)

import performance_eval as P  # noqa: E402


def test_deterministic_given_seed():
    a = P.run(seed=0, learners=60)
    b = P.run(seed=0, learners=60)
    assert a["accuracy"] == b["accuracy"]
    assert a["learned_weights"] == b["learned_weights"]


def test_concept_split_has_no_leakage():
    heldout = P.load_heldout()
    rows = P.build_rows(0, 40, heldout)
    train, test = P.split_by_concept(rows, heldout, 0)
    train_cids = {r["concept_id"] for r in train}
    test_cids = {r["concept_id"] for r in test}
    # A held-out concept (and thus BOTH its paraphrases) never appears in train.
    assert train_cids.isdisjoint(test_cids)
    assert test_cids  # something was actually held out
    assert train_cids  # something remains to train on
    # Both variants of a test concept are in the test split, not split apart.
    for cid in test_cids:
        variants = {r["variant"] for r in test if r["concept_id"] == cid}
        assert variants == {"question_a", "question_b"}


def test_headline_accuracy_beats_baseline_across_seeds():
    # Beating the majority-class baseline is the robust invariant the model
    # must satisfy on every seed (accuracy itself has small-sample variance).
    for seed in range(6):
        m = P.run(seed=seed, learners=80)
        assert m["accuracy"] > m["majority_baseline_acc"], seed
        assert m["beats_baseline"] is True, seed


def test_default_seed_passes_stated_gate():
    m = P.run(seed=0)
    assert m["accuracy"] >= P.ACCURACY_CUT
    assert m["gate_pass"] is True


def test_learned_weights_recover_true_signs():
    # The model never sees the true weights, but on enough data it should
    # recover their signs: mastery/coverage help, difficulty/timing hurt.
    m = P.run(seed=0, learners=200)
    w = m["learned_weights"]
    assert w["topic_mastery"] > 0
    assert w["coverage"] > 0
    assert w["difficulty"] < 0
    assert w["timing"] < 0


def test_standardization_uses_train_only():
    heldout = P.load_heldout()
    rows = P.build_rows(1, 30, heldout)
    train, _ = P.split_by_concept(rows, heldout, 1)
    means, stds = P._standardize(train)
    for f in P._FEATURES:
        xs = [r["features"][f] for r in train]
        assert abs(means[f] - sum(xs) / len(xs)) < 1e-12
        assert stds[f] > 0


def test_majority_baseline_math():
    # test base rate 0.6863 -> majority class 1 -> baseline == base rate.
    m = P.run(seed=0)
    assert abs(m["majority_baseline_acc"] - m["test_base_rate"]) < 1e-9


def test_simulated_label_and_exit_zero_on_pass():
    m = P.run(seed=0)
    assert m["simulated"] is True
    assert P.main([]) == 0  # default seed passes the gate -> exit 0
    assert P.main(["--seed", "7"]) == 1  # seed 7 dips below cut -> exit 1
