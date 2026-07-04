# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for A8 — the study-feature ablation harness (three builds).

Pure-Python (stdlib only), no built Anki required. Verifies the DGP is
deterministic, the fixed study budget is truly equal across arms, the
pre-registered effect is real in the base run, the honest uniform-weights
null control collapses the ON-OFF effect exactly, the give-up rule abstains,
the real-observations path drops the SIMULATED label and gates honestly, and
the exit-code contract holds.
"""

from __future__ import annotations

import importlib.util
import json
import os

import pytest

REPO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
TOOLS_CFA = os.path.join(REPO, "tools", "cfa")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A8 = _load("cfa_ablation", os.path.join(TOOLS_CFA, "ablation_harness.py"))


def test_weights_normalized_and_uniform_control():
    topics = A8.load_topics()
    assert len(topics) == 10
    w = A8.topic_weights(topics)
    assert abs(sum(w) - 1.0) < 1e-9
    # Real weights are NOT all equal (they are the official band midpoints).
    assert max(w) - min(w) > 1e-6
    u = A8.topic_weights(topics, uniform=True)
    assert all(abs(x - 0.1) < 1e-9 for x in u)


def test_simulation_is_deterministic():
    a = A8.simulate(seed=3, learners=80)
    b = A8.simulate(seed=3, learners=80)
    assert a["per_arm"] == b["per_arm"]
    c = A8.simulate(seed=4, learners=80)
    assert a["per_arm"] != c["per_arm"]


def test_budget_is_equal_across_arms():
    """The whole ablation rests on identical study time — assert the
    allocation for every arm spends exactly the budget."""
    topics = A8.load_topics()
    w = A8.topic_weights(topics)
    m0 = [0.5 - 0.03 * t for t in range(len(topics))]  # descending masteries
    budget = 37
    for arm in A8.ARMS:
        counts = A8._allocate(arm, w, m0, budget)
        assert sum(counts) == budget
        assert all(0 <= c <= A8.CARDS_PER_TOPIC for c in counts)


def test_allocation_policies_differ():
    """ON, OFF and PLAIN must pick different cards for a non-trivial cohort,
    otherwise the ablation is measuring nothing."""
    topics = A8.load_topics()
    w = A8.topic_weights(topics)
    # Exactly two equally-weak topics: a LOW-weight one at a lower index
    # (quant, idx 1) and a HIGH-weight one at a higher index (equity, idx 5).
    # With a one-topic budget the arms must diverge: OFF breaks the weakness
    # tie by index (picks idx 1), ON breaks it by exam weight (picks idx 5),
    # PLAIN ignores both and takes deck order (idx 0).
    m0 = [0.9, 0.2, 0.9, 0.9, 0.9, 0.2, 0.9, 0.9, 0.9, 0.9]
    budget = A8.CARDS_PER_TOPIC  # one topic's worth
    on = A8._allocate("on", w, m0, budget)
    off = A8._allocate("off", w, m0, budget)
    plain = A8._allocate("plain", w, m0, budget)
    assert on != off
    assert on != plain
    assert off != plain


def test_study_gain_monotone_and_capped():
    m0 = [0.3] * 10
    none = A8._post_study_mastery(m0, [0] * 10)
    assert none == m0
    partial = A8._post_study_mastery(m0, [A8.CARDS_PER_TOPIC // 2] * 10)
    full = A8._post_study_mastery(m0, [A8.CARDS_PER_TOPIC] * 10)
    for i in range(10):
        assert m0[i] <= partial[i] < full[i] <= 1.0
    # A fully studied topic closes exactly STUDY_GAIN of the remaining gap.
    assert abs(full[0] - (0.3 + 0.7 * A8.STUDY_GAIN)) < 1e-9


def test_pre_registered_effect_is_real():
    """Base run: ON should beat both OFF and PLAIN with a CI clearing zero."""
    m = A8.analyze(A8.simulate(seed=0, learners=200), seed=0)
    assert not m["abstain"]
    s = m["arm_stats"]
    assert s["on"]["mean"] > s["off"]["mean"] > s["plain"]["mean"]
    assert m["on_minus_off"]["ci_low"] > 0
    assert m["on_minus_plain"]["ci_low"] > 0


def test_uniform_weights_null_collapses_on_minus_off():
    """Honest null control: equal weights make ON's key identical to OFF's,
    so the ON-OFF effect must vanish exactly while ON still beats PLAIN."""
    sim = A8.simulate(seed=0, learners=200, uniform_weights=True)
    # Per-learner ON and OFF outcomes must be identical, arm for arm.
    assert sim["per_arm"]["on"] == sim["per_arm"]["off"]
    m = A8.analyze(sim, seed=0)
    assert m["on_minus_off"]["mean"] == 0.0
    assert m["on_minus_off"]["ci_low"] == 0.0 == m["on_minus_off"]["ci_high"]
    # ON-vs-PLAIN survives (deck order still ignores weakness).
    assert m["on_minus_plain"]["ci_low"] > 0


def test_effect_holds_across_seeds():
    """ON beats PLAIN on every seed; the weight-driven ON-OFF effect is
    positive on average (small-cohort seeds may not always clear zero)."""
    for seed in range(6):
        m = A8.analyze(A8.simulate(seed=seed, learners=200), seed=seed)
        assert m["on_minus_plain"]["ci_low"] > 0
        assert m["on_minus_off"]["mean"] > 0


def test_give_up_abstains_on_small_cohort():
    m = A8.analyze(A8.simulate(seed=0, learners=A8.MIN_LEARNERS - 1), seed=0)
    assert m["abstain"] is True
    # A SIMULATED abstain still exits 0 (honest give-up, not a failure).
    assert A8.main(["--learners", str(A8.MIN_LEARNERS - 1)]) == 0


def test_simulated_run_exits_zero():
    # SIMULATED is a measurement of the model, never a pass/fail gate.
    assert A8.main([]) == 0
    assert A8.main(["--uniform-weights"]) == 0
    assert A8.main(["--json"]) == 0


def test_real_observations_gate(tmp_path):
    """--observations drops the SIMULATED label and gates on the hypothesis:
    a build where ON wins passes (exit 0); one where it does not fails (1)."""
    good = tmp_path / "good.jsonl"
    with good.open("w") as fh:
        for i in range(60):
            # ON strictly best for every learner -> effect CIs clear zero.
            fh.write(json.dumps({
                "on": 0.80, "off": 0.70 + (i % 3) * 0.001,
                "plain": 0.60,
            }) + "\n")
    assert A8.main(["--observations", str(good)]) == 0

    bad = tmp_path / "bad.jsonl"
    with bad.open("w") as fh:
        for i in range(60):
            # ON no better than OFF -> ON-OFF null -> hypothesis fails.
            fh.write(json.dumps({
                "on": 0.70, "off": 0.70, "plain": 0.60,
            }) + "\n")
    assert A8.main(["--observations", str(bad)]) == 1


def test_from_observations_parses_all_arms(tmp_path):
    p = tmp_path / "obs.jsonl"
    rows = [{"on": 0.7, "off": 0.6, "plain": 0.5},
            {"on": 0.8, "off": 0.65, "plain": 0.55}]
    with p.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    sim = A8._from_observations(str(p))
    assert sim["learners"] == 2
    assert sim["per_arm"]["on"] == [0.7, 0.8]
    assert sim["budget_cards"] is None
