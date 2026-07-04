# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A5 tests — the paraphrase memory-vs-performance gap.

Stdlib only; no built pylib. Covers determinism, that memory (rote recall)
runs materially above performance (reworded accuracy), that the gap collapses
toward zero when the modelled rote advantage is removed, the bootstrap CI, the
give-up (abstain) rule, and the SIMULATED / real-observations contracts.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL_DIR = os.path.dirname(HERE)
sys.path.insert(0, EVAL_DIR)

import paraphrase_test as PT  # noqa: E402


def test_deterministic_given_seed():
    a = PT.analyze(PT.simulate_gap(seed=0, learners=80), seed=0)
    b = PT.analyze(PT.simulate_gap(seed=0, learners=80), seed=0)
    assert a["gap"] == b["gap"]
    assert a["gap_ci_low"] == b["gap_ci_low"]
    assert a["recall_rate"] == b["recall_rate"]


def test_memory_exceeds_performance():
    m = PT.analyze(PT.simulate_gap(seed=0, learners=200), seed=0)
    # Rote recall on the drilled card must beat reworded accuracy.
    assert m["recall_rate"] > m["transfer_rate"]
    assert m["gap"] > 0
    # And the effect is distinguishable from noise (CI clears zero).
    assert m["gap_ci_low"] > 0
    assert m["distinguishable"] is True


def test_gap_collapses_without_rote_boost():
    with_boost = PT.analyze(
        PT.simulate_gap(seed=1, learners=200, rote_boost=0.30), seed=1
    )
    no_boost = PT.analyze(
        PT.simulate_gap(seed=1, learners=200, rote_boost=0.0), seed=1
    )
    # Removing the modelled rote advantage should shrink the gap sharply.
    assert no_boost["gap"] < 0.05
    assert no_boost["gap"] < with_boost["gap"] / 2


def test_gap_monotonic_in_rote_boost():
    lo = PT.analyze(PT.simulate_gap(seed=2, learners=200, rote_boost=0.1), seed=2)
    hi = PT.analyze(PT.simulate_gap(seed=2, learners=200, rote_boost=0.5), seed=2)
    assert hi["gap"] > lo["gap"]


def test_bootstrap_ci_brackets_point_estimate():
    m = PT.analyze(PT.simulate_gap(seed=3, learners=200), seed=3)
    assert m["gap_ci_low"] <= m["gap"] <= m["gap_ci_high"]
    assert m["gap_ci_low"] <= m["gap_ci_high"]


def test_abstain_on_too_few_learners():
    m = PT.analyze(PT.simulate_gap(seed=0, learners=5), seed=0)
    assert m["abstain"] is True
    assert "insufficient data" in m["reason"]


def test_abstain_on_too_few_concepts(tmp_path):
    heldout = PT.load_heldout()[:5]
    small = tmp_path / "small.jsonl"
    small.write_text("\n".join(json.dumps(x) for x in heldout), encoding="utf-8")
    m = PT.analyze(
        PT.simulate_gap(seed=0, learners=200, heldout_path=str(small)), seed=0
    )
    assert m["abstain"] is True
    assert m["concepts"] == 5


def test_observations_path_drops_simulated_label(tmp_path):
    # Real per-attempt outcomes: recall always right, transfer split -> gap>0.
    rows = []
    for learner in range(40):
        for concept in range(12):
            transferred = 1 if (learner + concept) % 2 == 0 else 0
            rows.append(
                {
                    "learner": learner,
                    "concept_id": f"c{concept}",
                    "recalled": 1,
                    "transferred": transferred,
                }
            )
    obs = tmp_path / "obs.jsonl"
    obs.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    sim = PT._from_observations(str(obs))
    assert sim["rote_boost"] is None
    m = PT.analyze(sim, seed=0)
    assert m["recall_rate"] == 1.0
    assert 0.3 < m["transfer_rate"] < 0.7
    assert m["gap"] > 0
    # Real, distinguishable data -> main() exits 0.
    assert PT.main(["--observations", str(obs)]) == 0


def test_real_non_distinguishable_observations_exit_one(tmp_path):
    # Recall == transfer everywhere -> gap 0 -> not distinguishable -> exit 1.
    rows = []
    for learner in range(40):
        for concept in range(12):
            v = (learner + concept) % 2
            rows.append(
                {
                    "learner": learner,
                    "concept_id": f"c{concept}",
                    "recalled": v,
                    "transferred": v,
                }
            )
    obs = tmp_path / "flat.jsonl"
    obs.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    m = PT.analyze(PT._from_observations(str(obs)), seed=0)
    assert abs(m["gap"]) < 1e-9
    assert m["distinguishable"] is False
    assert PT.main(["--observations", str(obs)]) == 1


def test_simulated_main_exits_zero():
    # A SIMULATED run is a measurement of the model; it exits 0 when it does
    # not abstain, regardless of the gate (the gate only fails REAL data).
    assert PT.main([]) == 0
    assert PT.main(["--json"]) == 0
    # Abstaining is a valid honest give-up, also exit 0.
    assert PT.main(["--learners", "5"]) == 0
