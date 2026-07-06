#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A8 — study-feature ablation across three builds at equal study time.

THE FEATURE UNDER TEST
----------------------
The **exam-priority "points-at-stake" study queue** (the `BuildExamQueue` RPC).
It scores each studyable card by ``topic_weight * (1 - retrievability)`` — i.e.
it spends your limited study time where the *most exam points are at stake*
(a high-weight topic you are weak on) instead of in deck order.

THE HYPOTHESIS (one sentence, pre-registered)
---------------------------------------------
At an **equal study-time budget** on the **same cohort and the same held-out
exam**, allocating study by points-at-stake (exam-weight x weakness) yields a
higher **exam-weighted accuracy** than allocating by weakness alone or by plain
deck order.

THE THREE BUILDS (identical cohort, deck, exam, and budget — only the queue
policy differs, so any difference is attributable to the feature)
------------------------------------------------------------------
* **ON  — CFA app, exam-priority queue enabled.** Study the B cards with the
  highest ``exam_weight * weakness``. (What our RPC ships.)
* **OFF — CFA app, exam-priority queue disabled.** Study the B *weakest* cards,
  ignoring exam weight (a plausible "just review what you're worst at" fallback).
* **PLAIN — unmodified Anki.** Study the first B cards in deck (curriculum)
  order, ignoring both weakness and exam weight.

THE METRIC (pre-registered, reported WITH A RANGE)
--------------------------------------------------
**Exam-weighted accuracy**: after the fixed study budget, each learner sits a
held-out exam (``EXAM_Q_PER_TOPIC`` questions per topic); a question in topic
``t`` counts ``weight_t``. We report each arm's mean with a **percentile
bootstrap 95% CI over learners**, and the ON-minus-OFF / ON-minus-PLAIN
**effect sizes with their CIs**. An effect whose CI clears zero is real; one
that does not is reported honestly as a **null**.

HONESTY (non-negotiable)
------------------------
* The cohort is a SEEDED SIMULATION (no real study logs), so every run is
  labelled ``SIMULATED``; the numbers validate the *mechanism and the
  measurement*, not a real-world effect size. Pass ``--observations FILE`` to
  score real per-learner arm outcomes instead (the label is then dropped).
* **Honest null control** (``--uniform-weights``): make every topic weight
  equal. The ON sort key (weight x weakness) then collapses to the OFF key
  (weakness), so the ON-minus-OFF effect must vanish. If it does, the ON
  advantage in the real run is *caused by exam-weighting*, not an artifact.
* No AI is involved anywhere, so this runs identically with AI switched off.

Stdlib only; deterministic given ``--seed``; no build required.
Metric convention: exam-weighted accuracy in [0, 1], higher is better.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TOPICS_JSON = os.path.join(REPO, "cfa", "outline", "level2_topics.json")

# Logistic steepness mapping (mastery - difficulty) -> P(correct). Matches
# run_eval.K / anki.cfa's readiness logistic so the whole run is consistent.
K = 6.0

# Cohort / deck / study-budget defaults for the SIMULATED arm.
DEFAULT_LEARNERS = 200
CARDS_PER_TOPIC = 12  # a fresh, one-pass deck: each card studied 0/1x
EXAM_Q_PER_TOPIC = 6  # held-out exam questions per topic
# Fraction of the remaining mastery gap a *fully* studied topic closes. Studying
# k of a topic's cards closes (k / CARDS_PER_TOPIC) of that fraction — so study
# has diminishing returns per topic and a per-topic ceiling (you can't pour
# unlimited budget into one topic; it only has so many cards).
STUDY_GAIN = 0.80
# Study budget as a fraction of the whole deck. < 1 so allocation MATTERS: you
# cannot study everything, and where you spend the budget is the whole point.
DEFAULT_BUDGET_FRAC = 0.35

# Give-up thresholds: below these we ABSTAIN rather than report a noisy number.
MIN_LEARNERS = 30
MIN_BUDGET_CARDS = 1

ARMS = ("on", "off", "plain")
ARM_LABEL = {
    "on": "ON    (points-at-stake queue)",
    "off": "OFF   (weakness-only, no weight)",
    "plain": "PLAIN (unmodified Anki, deck order)",
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def load_topics(path: str = TOPICS_JSON) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["topics"]


def topic_weights(topics: list[dict], uniform: bool = False) -> list[float]:
    """Normalized exam weights (band midpoints), summing to 1.

    ``uniform=True`` returns equal weights — the honest null control that
    collapses the ON policy onto the OFF policy.
    """
    n = len(topics)
    if uniform:
        return [1.0 / n] * n
    mids = [(t["weight_low"] + t["weight_high"]) / 2.0 for t in topics]
    total = sum(mids)
    return [m / total for m in mids]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _bootstrap_ci(
    per_learner: list[float], seed: int, resamples: int = 2000
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for the mean of a per-learner quantity."""
    n = len(per_learner)
    if n == 0:
        return (float("nan"), float("nan"))
    rng = random.Random(seed ^ 0x5EED)
    means = []
    for _ in range(resamples):
        s = sum(per_learner[rng.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * resamples)]
    hi = means[min(resamples - 1, int(0.975 * resamples))]
    return (lo, hi)


def _allocate(
    arm: str, weights: list[float], m0: list[float], budget: int
) -> list[int]:
    """How many of each topic's cards the given ARM studies, for one learner.

    Returns a per-topic count in [0, CARDS_PER_TOPIC] summing to ``budget``.
    Each arm ranks the deck's cards differently, then fills the budget:

    * ``on``    — by ``weight_t * weakness_t`` (points at stake).
    * ``off``   — by ``weakness_t`` alone (ignores exam weight).
    * ``plain`` — by fixed deck/curriculum order (ignores both).
    """
    n = len(weights)
    weakness = [1.0 - m0[t] for t in range(n)]
    if arm == "on":
        key = [weights[t] * weakness[t] for t in range(n)]
        order = sorted(range(n), key=lambda t: (-key[t], t))
    elif arm == "off":
        order = sorted(range(n), key=lambda t: (-weakness[t], t))
    elif arm == "plain":
        order = list(range(n))  # curriculum order, as authored in the outline
    else:
        raise ValueError(f"unknown arm {arm!r}")

    counts = [0] * n
    remaining = budget
    for t in order:
        take = min(CARDS_PER_TOPIC, remaining)
        counts[t] = take
        remaining -= take
        if remaining <= 0:
            break
    return counts


def _post_study_mastery(m0: list[float], counts: list[int]) -> list[float]:
    """Mastery per topic after studying ``counts[t]`` of its cards.

    Diminishing returns with a per-topic ceiling: studying all
    ``CARDS_PER_TOPIC`` cards closes ``STUDY_GAIN`` of the (1 - m0) gap.
    """
    out = []
    for t, m in enumerate(m0):
        frac = counts[t] / CARDS_PER_TOPIC
        out.append(m + (1.0 - m) * STUDY_GAIN * frac)
    return out


def simulate(
    seed: int = 0,
    learners: int = DEFAULT_LEARNERS,
    budget_frac: float = DEFAULT_BUDGET_FRAC,
    uniform_weights: bool = False,
    topics_path: str = TOPICS_JSON,
) -> dict:
    """Seeded three-arm ablation DGP. Deterministic given ``seed``.

    Every arm sees the SAME learners, the SAME starting masteries, the SAME
    held-out exam questions, and the SAME study budget — only the allocation
    policy differs. Returns per-learner exam-weighted accuracy for each arm.
    """
    topics = load_topics(topics_path)
    n_topics = len(topics)
    weights = topic_weights(topics, uniform=uniform_weights)
    total_cards = n_topics * CARDS_PER_TOPIC
    budget = max(0, min(total_cards, round(budget_frac * total_cards)))

    rng = random.Random(seed)
    # Per-topic exam-question difficulties: fixed held-out exam, shared by all
    # arms and all learners (drawn once so the exam is identical across arms).
    exam_diff = [
        [rng.uniform(0.25, 0.75) for _ in range(EXAM_Q_PER_TOPIC)]
        for _ in range(n_topics)
    ]

    per_arm: dict[str, list[float]] = {a: [] for a in ARMS}
    for _ in range(learners):
        # This learner's starting per-topic mastery (room to improve). Same
        # vector fed to all three arms.
        m0 = [rng.betavariate(4, 5) for _ in range(n_topics)]
        # A single stream of exam Bernoulli draws, reused across arms so the
        # only thing that moves an arm's score is its post-study mastery.
        exam_u = [
            [rng.random() for _ in range(EXAM_Q_PER_TOPIC)] for _ in range(n_topics)
        ]
        for arm in ARMS:
            counts = _allocate(arm, weights, m0, budget)
            m = _post_study_mastery(m0, counts)
            num = den = 0.0
            for t in range(n_topics):
                for q in range(EXAM_Q_PER_TOPIC):
                    p = _sigmoid(K * (m[t] - exam_diff[t][q]))
                    correct = 1.0 if exam_u[t][q] < p else 0.0
                    num += weights[t] * correct
                    den += weights[t]
            per_arm[arm].append(num / den)

    return {
        "per_arm": per_arm,
        "learners": learners,
        "topics": n_topics,
        "budget_cards": budget,
        "total_cards": total_cards,
        "budget_frac": budget_frac,
        "uniform_weights": uniform_weights,
        "exam_questions": n_topics * EXAM_Q_PER_TOPIC,
    }


def _from_observations(path: str) -> dict:
    """Score REAL per-learner arm outcomes instead of the simulation.

    Expects a JSONL file, one object per learner with float fields ``on``,
    ``off`` and ``plain`` — each learner's exam-weighted accuracy under each
    build. No simulation, no SIMULATED label.
    """
    per_arm: dict[str, list[float]] = {a: [] for a in ARMS}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for a in ARMS:
                per_arm[a].append(float(row[a]))
    learners = len(per_arm["on"])
    return {
        "per_arm": per_arm,
        "learners": learners,
        "topics": None,
        "budget_cards": None,
        "total_cards": None,
        "budget_frac": None,
        "uniform_weights": False,
        "exam_questions": None,
    }


def _paired_diff_ci(
    a: list[float], b: list[float], seed: int
) -> tuple[float, float, float]:
    """Mean paired difference (a - b) and its bootstrap 95% CI."""
    diffs = [x - y for x, y in zip(a, b)]
    lo, hi = _bootstrap_ci(diffs, seed=seed)
    return (_mean(diffs), lo, hi)


def analyze(sim: dict, seed: int = 0) -> dict:
    per = sim["per_arm"]
    learners = sim["learners"]
    give_up = learners < MIN_LEARNERS or (
        sim["budget_cards"] is not None and sim["budget_cards"] < MIN_BUDGET_CARDS
    )
    if give_up:
        return {
            "abstain": True,
            "learners": learners,
            "budget_cards": sim["budget_cards"],
            **sim,
        }

    arm_stats = {}
    for a in ARMS:
        lo, hi = _bootstrap_ci(per[a], seed=seed)
        arm_stats[a] = {"mean": _mean(per[a]), "ci_low": lo, "ci_high": hi}

    on_off = _paired_diff_ci(per["on"], per["off"], seed=seed + 1)
    on_plain = _paired_diff_ci(per["on"], per["plain"], seed=seed + 2)

    return {
        "abstain": False,
        "arm_stats": arm_stats,
        "on_minus_off": {"mean": on_off[0], "ci_low": on_off[1], "ci_high": on_off[2]},
        "on_minus_plain": {
            "mean": on_plain[0],
            "ci_low": on_plain[1],
            "ci_high": on_plain[2],
        },
        **sim,
    }


def _fmt(m: dict, simulated: bool) -> str:
    tag = "SIMULATED" if simulated else "REAL DATA"
    lines = [
        f"A8 study-feature ablation — exam-priority queue [{tag}]",
        "=" * 68,
        "FEATURE   : exam-priority points-at-stake study queue (BuildExamQueue)",
        "HYPOTHESIS: at equal study time, allocating by exam-weight x weakness",
        "            beats weakness-only and plain deck order on exam-weighted",
        "            accuracy.",
        "METRIC    : exam-weighted accuracy in [0,1] (higher better), "
        "95% CI over learners",
        "-" * 68,
    ]
    if m.get("abstain"):
        lines += [
            "RESULT    : ABSTAIN — insufficient data to estimate an effect.",
            f"  learners={m['learners']} (need >= {MIN_LEARNERS}); "
            f"budget_cards={m['budget_cards']} (need >= {MIN_BUDGET_CARDS})",
        ]
        return "\n".join(lines)

    if m["budget_cards"] is not None:
        lines += [
            f"cohort    : {m['learners']} learners x {m['topics']} topics",
            f"study time: {m['budget_cards']}/{m['total_cards']} cards "
            f"({m['budget_frac']:.0%} of deck) — SAME budget for all 3 arms",
            f"exam      : {m['exam_questions']} held-out questions "
            f"({EXAM_Q_PER_TOPIC}/topic), identical across arms",
        ]
    else:
        lines += [f"cohort    : {m['learners']} learners (real observations)"]
    if m.get("uniform_weights"):
        lines += ["control   : UNIFORM WEIGHTS (null) — ON key collapses onto OFF key"]
    lines += ["-" * 68, "Per-arm exam-weighted accuracy (mean [95% CI]):"]
    for a in ARMS:
        s = m["arm_stats"][a]
        lines.append(
            f"  {ARM_LABEL[a]:36s}: {s['mean']:.4f} "
            f"[{s['ci_low']:.4f}, {s['ci_high']:.4f}]"
        )

    def _eff(name: str, d: dict) -> str:
        clears = d["ci_low"] > 0
        verdict = "REAL effect (CI clears 0)" if clears else "NULL (CI includes 0)"
        return (
            f"  {name:22s}: {d['mean']:+.4f} "
            f"[{d['ci_low']:+.4f}, {d['ci_high']:+.4f}]  -> {verdict}"
        )

    lines += [
        "-" * 68,
        "Effect sizes (paired, bootstrap 95% CI):",
        _eff("ON - OFF", m["on_minus_off"]),
        _eff("ON - PLAIN", m["on_minus_plain"]),
    ]
    if simulated:
        lines += [
            "-" * 68,
            "NOTE: SIMULATED cohort — validates the mechanism + the metric, not",
            "      a real-world effect size. Re-run with --uniform-weights to",
            "      confirm the ON-OFF effect is driven by exam-weighting, and",
            "      --observations FILE to score real per-learner arm outcomes.",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A8 study-feature ablation (3 builds)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--learners", type=int, default=DEFAULT_LEARNERS)
    ap.add_argument(
        "--budget-frac",
        type=float,
        default=DEFAULT_BUDGET_FRAC,
        help="study budget as a fraction of the deck (0..1)",
    )
    ap.add_argument(
        "--uniform-weights",
        action="store_true",
        help="honest null control: equal topic weights",
    )
    ap.add_argument(
        "--observations",
        metavar="FILE",
        help="score real per-learner arm outcomes (JSONL); drops the SIMULATED label",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    args = ap.parse_args(argv)

    if args.observations:
        sim = _from_observations(args.observations)
        simulated = False
    else:
        sim = simulate(
            seed=args.seed,
            learners=args.learners,
            budget_frac=args.budget_frac,
            uniform_weights=args.uniform_weights,
        )
        simulated = True

    m = analyze(sim, seed=args.seed)
    if args.json:
        printable = {k: v for k, v in m.items() if k != "per_arm"}
        print(json.dumps(printable, indent=2, default=str))
    else:
        print(_fmt(m, simulated=simulated))

    # Exit-code contract (mirrors the other A-evals):
    #  * abstain -> 0 (honest give-up, not a failure)
    #  * SIMULATED -> 0 (a measurement of the model, never a pass/fail gate)
    #  * REAL observations -> 1 if the pre-registered hypothesis fails
    #    (ON does not beat both OFF and PLAIN with a CI clearing zero).
    if m.get("abstain") or simulated:
        return 0
    on_off_ok = m["on_minus_off"]["ci_low"] > 0
    on_plain_ok = m["on_minus_plain"]["ci_low"] > 0
    return 0 if (on_off_ok and on_plain_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
