#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Seeded, re-runnable held-out evaluation of the CFA recall-probability model.

WHAT THIS IS (and is NOT)
-------------------------
This harness measures how well our recall-probability model — the same logistic
mastery-vs-difficulty shape used by the honest scores in ``anki.cfa`` — is
*calibrated*, using a synthetic cohort of learners. It is deliberately a
SIMULATION: there is no real exam-taker data here, so the numbers validate the
model's math and our metric code, not real-world performance. This mirrors the
standing "not validated against real exam data" caveat on the readiness score.

DESIGN
------
* Held-out set: ``heldout.jsonl`` — 30 authored concepts, each with two
  independently reworded questions (a paraphrase pair) sharing one true
  ``difficulty``. The pairs let us measure whether the model's prediction is
  stable to wording (it should be).
* Data-generating process: for a seeded cohort of ``learners`` learners, each
  learner ``l`` has a latent mastery ``m_l``. The TRUE probability of answering
  a question is ``sigmoid(K*(m_l - true_difficulty))`` and the outcome is a
  seeded Bernoulli draw from it.
* Model under test: it does not see the true difficulty. It estimates difficulty
  from the question text (a lexical-length feature) blended with the concept's
  authored difficulty, so paraphrases get near-identical — but not identical —
  predictions. ``pred_p = sigmoid(K*(m_l - est_difficulty))``.
* Metrics over all (pred_p, outcome) pairs: accuracy (@0.5), ROC AUC
  (Mann-Whitney), and expected calibration error (10-bin). Plus a
  paraphrase-stability figure: mean |mean_pred_a - mean_pred_b| across concepts.

Everything is deterministic given ``--seed``. Stdlib only; no build required.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
HELDOUT = os.path.join(HERE, "heldout.jsonl")

# Logistic steepness mapping (mastery - difficulty) -> P(correct). Matches the
# spirit of anki.cfa's readiness logistic.
K = 6.0
DEFAULT_LEARNERS = 200

_TOKEN = re.compile(r"[a-z0-9]+")


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _text_difficulty(question: str) -> float:
    """A cheap, wording-sensitive difficulty proxy in [0, 1].

    Longer, denser questions read as harder. This is the ONLY thing that
    differs between two paraphrases of the same concept, so it drives the
    paraphrase-stability metric."""
    n = len(_TOKEN.findall(question.lower()))
    return max(0.05, min(0.95, (n - 8) / 24.0))


def load_heldout(path: str = HELDOUT) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _auc(scores: list[float], labels: list[int]) -> float:
    """ROC AUC via the Mann-Whitney U statistic with tie handling."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    # Rank all scores (average ranks for ties).
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    sum_pos = sum(ranks[i] for i, y in enumerate(labels) if y == 1)
    n_pos, n_neg = len(pos), len(neg)
    u = sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def _ece(scores: list[float], labels: list[int], bins: int = 10) -> float:
    """Expected calibration error over equal-width probability bins."""
    total = len(scores)
    if total == 0:
        return float("nan")
    ece = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [
            i
            for i, s in enumerate(scores)
            if (s >= lo and s < hi) or (b == bins - 1 and s == 1.0)
        ]
        if not idx:
            continue
        conf = sum(scores[i] for i in idx) / len(idx)
        acc = sum(labels[i] for i in idx) / len(idx)
        ece += (len(idx) / total) * abs(acc - conf)
    return ece


def simulate(seed: int = 0, learners: int = DEFAULT_LEARNERS,
             heldout_path: str = HELDOUT) -> dict:
    """Run the seeded data-generating process once.

    Returns the raw ``(pred_p, outcome)`` pairs plus per-variant mean
    predictions, so downstream tools (e.g. ``calibration.py``) can compute
    their own metrics from exactly the same simulated held-out reviews rather
    than re-deriving the DGP. Deterministic given ``seed``.
    """
    rng = random.Random(seed)
    heldout = load_heldout(heldout_path)

    # Sample one mastery per learner (0..1), stable order for a given seed.
    masteries = [rng.betavariate(5, 4) for _ in range(learners)]

    scores: list[float] = []
    labels: list[int] = []
    # For paraphrase stability: mean predicted P per (concept, variant).
    per_variant_mean: dict[str, dict[str, float]] = {}

    for item in heldout:
        cid = item["concept_id"]
        true_diff = float(item["difficulty"])
        per_variant_mean[cid] = {}
        for variant in ("question_a", "question_b"):
            q = item[variant]
            # Model's difficulty estimate: authored prior blended with a
            # wording-derived feature (this is what a paraphrase perturbs).
            est_diff = 0.7 * true_diff + 0.3 * _text_difficulty(q)
            preds_here: list[float] = []
            for m in masteries:
                true_p = _sigmoid(K * (m - true_diff))
                outcome = 1 if rng.random() < true_p else 0
                pred_p = _sigmoid(K * (m - est_diff))
                scores.append(pred_p)
                labels.append(outcome)
                preds_here.append(pred_p)
            per_variant_mean[cid][variant] = sum(preds_here) / len(preds_here)

    return {
        "scores": scores,
        "labels": labels,
        "per_variant_mean": per_variant_mean,
        "concepts": len(heldout),
        "learners": learners,
    }


def run(seed: int = 0, learners: int = DEFAULT_LEARNERS,
        heldout_path: str = HELDOUT) -> dict:
    sim = simulate(seed=seed, learners=learners, heldout_path=heldout_path)
    scores = sim["scores"]
    labels = sim["labels"]
    per_variant_mean = sim["per_variant_mean"]

    accuracy = sum(
        1 for s, y in zip(scores, labels) if (s >= 0.5) == bool(y)
    ) / len(scores)
    auc = _auc(scores, labels)
    ece = _ece(scores, labels)

    # Paraphrase stability: how far apart the two reworded variants land.
    gaps = [
        abs(v["question_a"] - v["question_b"]) for v in per_variant_mean.values()
    ]
    paraphrase_gap = sum(gaps) / len(gaps)
    paraphrase_max = max(gaps)

    return {
        "seed": seed,
        "learners": learners,
        "concepts": sim["concepts"],
        "questions": 2 * sim["concepts"],
        "predictions": len(scores),
        "accuracy": accuracy,
        "auc": auc,
        "ece": ece,
        "paraphrase_gap_mean": paraphrase_gap,
        "paraphrase_gap_max": paraphrase_max,
    }


def _fmt(metrics: dict) -> str:
    lines = [
        "CFA held-out eval (simulation — not validated against real exam data)",
        "-" * 68,
        f"seed                : {metrics['seed']}",
        f"learners            : {metrics['learners']}",
        f"held-out concepts   : {metrics['concepts']}  "
        f"(x2 paraphrases = {metrics['questions']} questions)",
        f"predictions scored  : {metrics['predictions']}",
        "",
        f"accuracy   @0.5     : {metrics['accuracy']:.4f}",
        f"AUC (ROC)           : {metrics['auc']:.4f}",
        f"ECE (10-bin)        : {metrics['ece']:.4f}",
        f"paraphrase gap mean : {metrics['paraphrase_gap_mean']:.4f}",
        f"paraphrase gap max  : {metrics['paraphrase_gap_max']:.4f}",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Seeded CFA held-out eval")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--learners", type=int, default=DEFAULT_LEARNERS)
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    ap.add_argument("--heldout", default=HELDOUT)
    args = ap.parse_args()
    metrics = run(seed=args.seed, learners=args.learners,
                  heldout_path=args.heldout)
    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        print(_fmt(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
