# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A6 tests — card-generation gold-set checker.

No ``anki`` dependency and no network: the real generator is driven by an
injected ``complete_fn`` oracle. Covers the 3-way classifier (correct+useful /
correct-but-bad / wrong), the declared cutoff gate, the honest SIMULATED exit
contract, the give-up/abstain rule, and that a bad real batch is BLOCKED.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(EVAL))
sys.path.insert(0, EVAL)
sys.path.insert(0, REPO)

import cardgen_check as C  # noqa: E402


# --- gold set ----------------------------------------------------------------


def test_gold_set_loads_50_wellformed():
    gold = C.load_gold()
    assert len(gold) == 50
    ids = [g["id"] for g in gold]
    assert len(set(ids)) == 50  # unique ids
    for g in gold:
        assert g["front"].strip()
        assert g["gold_back"].strip()
        assert g["topic"]
    # spread across the 10 canonical areas, not one topic
    assert len({g["topic"] for g in gold}) >= 8


# --- classifier --------------------------------------------------------------


def test_classify_correct_useful_on_exact_gold():
    g = "The spot price is for immediate delivery; the futures price is agreed today."
    res = C.classify_card(g, g, front="What is the spot vs futures price?")
    assert res["bucket"] == "correct_useful"
    assert res["coverage"] == 1.0


def test_classify_wrong_when_off_topic():
    gold = "Roll return, price return, and collateral return are the components."
    gen = "Duration measures interest-rate sensitivity of a bond's price."
    res = C.classify_card(gold, gen)
    assert res["bucket"] == "wrong"
    assert res["coverage"] < C.COVERAGE_WRONG


def test_classify_wrong_on_empty():
    res = C.classify_card("anything correct here", "   ")
    assert res["bucket"] == "wrong"
    assert res["reason"] == "empty"


def test_classify_correct_but_bad_too_short():
    # a short-but-on-target stub: keeps coverage yet is too terse to be useful
    gold = "Roll yield return."
    res = C.classify_card(gold, "Roll yield.")
    assert res["coverage"] >= C.COVERAGE_WRONG
    assert res["bucket"] == "correct_but_bad"
    assert "short" in res["reason"]


def test_classify_correct_but_bad_rambling():
    gold = "Beta measures systematic risk relative to the market portfolio."
    gen = (gold + " ") * 15  # correct facts, rambling wall of text
    res = C.classify_card(gold, gen)
    assert res["bucket"] == "correct_but_bad"
    assert res["coverage"] == 1.0


def test_classify_correct_but_bad_circular_echo():
    front = "Under Standard IV(A) Loyalty what is the duty to an employer"
    gold = "Under Standard IV(A) Loyalty the duty to an employer is act benefit"
    # a draft that just parrots the question back verbatim
    res = C.classify_card(gold, front, front=front)
    assert res["bucket"] == "correct_but_bad"
    assert "circular" in res["reason"]


# --- simulated generator + gate ---------------------------------------------


def test_simulated_default_passes_and_exits_zero():
    gold = C.load_gold()
    gen = C.simulate_generation(gold, seed=0)
    rep = C.run_check(gold, gen, ran_ai=False, simulated=True)
    assert rep["gate_pass"] is True
    assert rep["correct_useful_fraction"] >= C.USEFUL_CUT
    assert rep["wrong_fraction"] <= C.WRONG_CUT
    # all three buckets are exercised
    assert rep["counts"]["wrong"] > 0
    assert rep["counts"]["correct_but_bad"] > 0
    assert rep["counts"]["correct_useful"] > 0
    # SIMULATED run is a measurement -> exits 0 even though real batches block
    assert C.main([]) == 0


def test_simulated_is_deterministic():
    gold = C.load_gold()
    a = C.simulate_generation(gold, seed=0)
    b = C.simulate_generation(gold, seed=0)
    assert a == b
    c = C.simulate_generation(gold, seed=1)
    assert a != c  # a different seed reshuffles which rows are perturbed


def test_bad_sim_fails_gate_but_simulated_still_exits_zero():
    gold = C.load_gold()
    gen = C.simulate_generation(gold, seed=0, bad=True)
    rep = C.run_check(gold, gen, ran_ai=False, simulated=True)
    assert rep["gate_pass"] is False
    assert rep["wrong_fraction"] > C.WRONG_CUT
    # honest AI-off contract: a SIMULATED failing batch still exits 0
    assert C.main(["--bad-sim"]) == 0


def test_abstain_below_min_gold():
    gold = C.load_gold()[: C.MIN_GOLD - 1]
    gen = C.simulate_generation(gold, seed=0)
    rep = C.run_check(gold, gen, ran_ai=False, simulated=True)
    assert rep["abstain"] is True
    txt = C.format_report(rep)
    assert "ABSTAIN" in txt


# --- real generator (injected oracle) ---------------------------------------


def _good_oracle(gold):
    """A complete_fn that returns the correct gold answer for each front."""
    by_front = {g["front"].strip(): g["gold_back"] for g in gold}

    def fn(system, user, **kwargs):
        for front, back in by_front.items():
            if front in user:
                return {"ok": True, "text": back, "model": "oracle", "usage": {},
                        "error": None, "purpose": kwargs.get("purpose", "")}
        return {"ok": True, "text": "unrelated filler text", "model": "oracle",
                "usage": {}, "error": None, "purpose": ""}

    return fn


def _bad_oracle(gold):
    """A complete_fn that returns a WRONG answer (a different item's) each time."""
    backs = [g["gold_back"] for g in gold]

    def fn(system, user, **kwargs):
        # always answer with the FIRST item's back -> wrong for all but one
        return {"ok": True, "text": backs[0], "model": "oracle", "usage": {},
                "error": None, "purpose": kwargs.get("purpose", "")}

    return fn


def _run_real(oracle):
    gold = C.load_gold()
    backs, ran_ai = C.generate_real(gold, complete_fn=oracle)
    return gold, backs, ran_ai


def test_real_good_generator_passes_gate():
    gold = C.load_gold()
    gold, backs, ran_ai = _run_real(_good_oracle(gold))
    assert ran_ai is True
    rep = C.run_check(gold, backs, ran_ai=ran_ai, simulated=False)
    assert rep["gate_pass"] is True
    assert rep["correct_useful_fraction"] >= C.USEFUL_CUT


def test_real_bad_generator_is_blocked():
    gold = C.load_gold()
    gold, backs, ran_ai = _run_real(_bad_oracle(gold))
    assert ran_ai is True
    rep = C.run_check(gold, backs, ran_ai=ran_ai, simulated=False)
    assert rep["gate_pass"] is False
    # a real batch that fails the cutoff is BLOCKED (non-zero) — the whole point
    assert rep["wrong_fraction"] > C.WRONG_CUT
