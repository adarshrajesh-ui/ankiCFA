#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A5 — the paraphrase memory-vs-performance gap.

WHY THIS EXISTS
---------------
The whole CFA app rests on one claim: **Memory** (can you recall the card you
drilled?) and **Performance** (can you answer a reworded, exam-style version of
the same idea?) are *different questions*. If they were the same, one score
would do. This harness measures the distance between them directly.

For each of the 30 held-out concepts we have two independently reworded
questions (a paraphrase pair) in ``heldout.jsonl``:

* ``question_a`` is treated as **the card the student drilled** — repeated
  exposure gives a rote-recall advantage (they have seen this exact wording).
* ``question_b`` is treated as **a fresh exam-style rewording** of the same LOS
  — no rote advantage; only genuine understanding transfers.

The *memory-vs-performance gap* is ``recall_rate - transfer_rate``: how much
higher rote recall of the drilled card runs than accuracy on the reworded
question, for the same cohort on the same concepts at the same difficulty.

HONESTY
-------
* Default cohort is a SEEDED SIMULATION (no real exam-taker data), so the run is
  labelled ``SIMULATED`` and the numbers validate the *measurement*, not a
  real-world effect size. Pass ``--observations FILE`` with real per-attempt
  outcomes to score actual data (the label is then dropped).
* We report a **range**, not a bare point estimate: a bootstrap 95% CI over the
  cohort. The honest question is whether the gap's CI clears zero — i.e. whether
  memory and performance are *distinguishable* — not whether it hits a target.
* Give-up rule: if the cohort or held-out set is too small to estimate a gap
  (< ``MIN_LEARNERS`` learners or < ``MIN_CONCEPTS`` concepts), we ABSTAIN
  rather than report a noisy number.
* No AI is involved at any point, so this runs identically with AI switched off.

Stdlib only; deterministic given ``--seed``; no build required.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from run_eval import HELDOUT, K, _sigmoid, _text_difficulty, load_heldout  # noqa: E402

# Give-up thresholds: below these we abstain instead of reporting a noisy gap.
MIN_LEARNERS = 30
MIN_CONCEPTS = 10

# Rote-recall advantage (in mastery units) from having drilled the *exact* card
# wording. This is the ONLY modelled difference between recalling the studied
# card and answering the reworded question; it is what produces the gap.
DEFAULT_ROTE_BOOST = 0.30
DEFAULT_LEARNERS = 200

# The gate is a *distinguishability* bar, not a target effect size: the 95% CI
# for the gap must clear zero (memory and performance are separable), and the
# point gap must be non-trivial.
GAP_MIN = 0.02


def _beta_masteries(seed: int, n: int) -> list[float]:
    """Seeded latent-mastery draws; matches run_eval's Beta(5,4) cohort shape."""
    import random

    rng = random.Random(seed)
    return [rng.betavariate(5, 4) for _ in range(n)]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _bootstrap_ci(
    per_learner_gap: list[float], seed: int, resamples: int = 2000
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for the mean per-learner gap."""
    import random

    n = len(per_learner_gap)
    if n == 0:
        return (float("nan"), float("nan"))
    rng = random.Random(seed ^ 0x5EED)
    means = []
    for _ in range(resamples):
        s = sum(per_learner_gap[rng.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * resamples)]
    hi = means[min(resamples - 1, int(0.975 * resamples))]
    return (lo, hi)


def simulate_gap(
    seed: int = 0,
    learners: int = DEFAULT_LEARNERS,
    rote_boost: float = DEFAULT_ROTE_BOOST,
    heldout_path: str = HELDOUT,
) -> dict:
    """Seeded DGP for the memory-vs-performance gap.

    For each learner (latent mastery ``m``) and concept (true ``difficulty``):

    * **Recall** on the drilled card ``question_a``:
      ``P = sigmoid(K*(m + rote_boost - diff))`` — rote exposure lifts the odds.
    * **Transfer** on the reworded ``question_b``:
      ``P = sigmoid(K*(m - diff))`` — no rote lift; wording only perturbs the
      difficulty estimate slightly.

    Outcomes are seeded Bernoulli draws. Returns per-learner recall/transfer
    rates and per-concept means so callers can compute their own aggregates.
    """
    import random

    rng = random.Random(seed)
    heldout = load_heldout(heldout_path)
    masteries = _beta_masteries(seed, learners)

    # Per-learner accumulators across all concepts.
    learner_recall = [0.0] * learners
    learner_transfer = [0.0] * learners
    per_concept: dict[str, dict[str, float]] = {}

    n_concepts = len(heldout)
    for item in heldout:
        cid = item["concept_id"]
        diff = float(item["difficulty"])
        # Wording nudges the reworded question's effective difficulty a touch,
        # but never grants a rote advantage.
        diff_b = min(0.98, diff + 0.15 * (_text_difficulty(item["question_b"]) - 0.5))
        rec_hits = trans_hits = 0
        for li, m in enumerate(masteries):
            p_recall = _sigmoid(K * (m + rote_boost - diff))
            p_transfer = _sigmoid(K * (m - diff_b))
            recalled = 1 if rng.random() < p_recall else 0
            transferred = 1 if rng.random() < p_transfer else 0
            learner_recall[li] += recalled
            learner_transfer[li] += transferred
            rec_hits += recalled
            trans_hits += transferred
        per_concept[cid] = {
            "recall": rec_hits / learners,
            "transfer": trans_hits / learners,
            "gap": (rec_hits - trans_hits) / learners,
        }

    learner_recall = [x / n_concepts for x in learner_recall]
    learner_transfer = [x / n_concepts for x in learner_transfer]
    return {
        "learner_recall": learner_recall,
        "learner_transfer": learner_transfer,
        "per_concept": per_concept,
        "concepts": n_concepts,
        "learners": learners,
        "rote_boost": rote_boost,
    }


def _from_observations(path: str) -> dict:
    """Score real per-attempt outcomes instead of the simulation.

    Expects a JSONL file, one object per (learner, concept) attempt pair with
    integer/bool fields ``recalled`` (studied card) and ``transferred``
    (reworded question), plus optional ``learner`` and ``concept_id`` ids.
    """
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    by_learner: dict[str, list[tuple[int, int]]] = {}
    by_concept: dict[str, list[tuple[int, int]]] = {}
    for i, r in enumerate(rows):
        rec = int(bool(r["recalled"]))
        tr = int(bool(r["transferred"]))
        lk = str(r.get("learner", i))
        ck = str(r.get("concept_id", i))
        by_learner.setdefault(lk, []).append((rec, tr))
        by_concept.setdefault(ck, []).append((rec, tr))
    learner_recall = [_mean([a for a, _ in v]) for v in by_learner.values()]
    learner_transfer = [_mean([b for _, b in v]) for v in by_learner.values()]
    per_concept = {
        c: {
            "recall": _mean([a for a, _ in v]),
            "transfer": _mean([b for _, b in v]),
            "gap": _mean([a for a, _ in v]) - _mean([b for _, b in v]),
        }
        for c, v in by_concept.items()
    }
    return {
        "learner_recall": learner_recall,
        "learner_transfer": learner_transfer,
        "per_concept": per_concept,
        "concepts": len(by_concept),
        "learners": len(by_learner),
        "rote_boost": None,
    }


def analyze(sim: dict, seed: int = 0) -> dict:
    """Turn a simulate/observation result into the reported gap metrics."""
    learners = sim["learners"]
    concepts = sim["concepts"]
    if learners < MIN_LEARNERS or concepts < MIN_CONCEPTS:
        return {
            "abstain": True,
            "reason": (
                f"insufficient data (learners={learners} < {MIN_LEARNERS} "
                f"or concepts={concepts} < {MIN_CONCEPTS})"
            ),
            "learners": learners,
            "concepts": concepts,
        }
    recall_rate = _mean(sim["learner_recall"])
    transfer_rate = _mean(sim["learner_transfer"])
    per_learner_gap = [
        r - t for r, t in zip(sim["learner_recall"], sim["learner_transfer"])
    ]
    gap = recall_rate - transfer_rate
    lo, hi = _bootstrap_ci(per_learner_gap, seed=seed)
    concept_gaps = [c["gap"] for c in sim["per_concept"].values()]
    return {
        "abstain": False,
        "learners": learners,
        "concepts": concepts,
        "rote_boost": sim["rote_boost"],
        "recall_rate": recall_rate,
        "transfer_rate": transfer_rate,
        "gap": gap,
        "gap_ci_low": lo,
        "gap_ci_high": hi,
        "concept_gap_min": min(concept_gaps),
        "concept_gap_max": max(concept_gaps),
        "concept_gap_mean": _mean(concept_gaps),
        # Distinguishable if the CI clears zero AND the gap is non-trivial.
        "distinguishable": (lo > 0.0) and (gap >= GAP_MIN),
    }


def _fmt(m: dict, simulated: bool) -> str:
    tag = "SIMULATED — not validated against real exam data" if simulated else "REAL"
    head = [
        f"CFA paraphrase memory-vs-performance gap [{tag}]",
        "=" * 68,
    ]
    if m.get("abstain"):
        head += [
            "RESULT: ABSTAIN (give-up rule)",
            f"reason: {m['reason']}",
        ]
        return "\n".join(head)
    verdict = "DISTINGUISHABLE" if m["distinguishable"] else "NOT DISTINGUISHABLE"
    boost = m["rote_boost"]
    lines = head + [
        f"learners            : {m['learners']}",
        f"held-out concepts   : {m['concepts']}  (x2 paraphrases)",
    ]
    if boost is not None:
        lines.append(f"rote boost (model)  : {boost:.2f} mastery units")
    lines += [
        "",
        f"MEMORY  recall rate (drilled card question_a)  : {m['recall_rate']:.4f}",
        f"PERFORMANCE accuracy (reworded    question_b)  : {m['transfer_rate']:.4f}",
        "-" * 68,
        f"memory-vs-performance GAP                      : {m['gap']:.4f}",
        f"  bootstrap 95% CI                             : "
        f"[{m['gap_ci_low']:.4f}, {m['gap_ci_high']:.4f}]",
        f"  per-concept gap  (min / mean / max)          : "
        f"{m['concept_gap_min']:.4f} / {m['concept_gap_mean']:.4f} / "
        f"{m['concept_gap_max']:.4f}",
        "",
        f"VERDICT: memory and performance are {verdict}"
        f" (CI clears 0: {m['gap_ci_low'] > 0}; gap>={GAP_MIN}: {m['gap'] >= GAP_MIN})",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A5 paraphrase memory-vs-performance gap")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--learners", type=int, default=DEFAULT_LEARNERS)
    ap.add_argument("--rote-boost", type=float, default=DEFAULT_ROTE_BOOST)
    ap.add_argument("--heldout", default=HELDOUT)
    ap.add_argument(
        "--observations",
        default=None,
        help="JSONL of real (recalled, transferred) attempts; drops SIMULATED",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    args = ap.parse_args(argv)

    simulated = args.observations is None
    if simulated:
        sim = simulate_gap(
            seed=args.seed,
            learners=args.learners,
            rote_boost=args.rote_boost,
            heldout_path=args.heldout,
        )
    else:
        sim = _from_observations(args.observations)

    metrics = analyze(sim, seed=args.seed)
    if args.json:
        print(json.dumps({"simulated": simulated, **metrics}, indent=2))
    else:
        print(_fmt(metrics, simulated=simulated))

    # Honest exit code: only fail when a *real* measurement is not
    # distinguishable. A SIMULATED run is a measurement of our model, so it
    # exits 0 as long as it did not abstain; abstaining exits 0 too (it is a
    # valid, honest give-up, not an error).
    if metrics.get("abstain"):
        return 0
    if not simulated and not metrics["distinguishable"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
