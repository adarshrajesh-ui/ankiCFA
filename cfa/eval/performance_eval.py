#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A4 — performance-model accuracy on held-out exam-style questions.

WHAT THIS IS (and is NOT)
-------------------------
A3 (``calibration.py``) asks *how well-calibrated* our recall-probability model
is. A4 asks a different, harder question: given what we know about a student —
their **topic mastery**, the question's **difficulty**, their answer **timing**,
and how much of the topic they've **covered** — can we PREDICT whether they'll
get a brand-new exam-style question right, and how ACCURATE is that prediction
on questions the model never trained on?

This is a SIMULATION. There is no real exam-taker data, so the numbers validate
the performance model's math and our train/test discipline, not real-world
outcomes. This mirrors the standing "not validated against real exam data"
caveat on the readiness score. Everything is deterministic given ``--seed``.

DESIGN
------
* Cohort: a seeded set of ``learners`` synthetic learners, each with a latent
  per-topic mastery vector.
* Questions: the 30 authored concepts in ``heldout.jsonl`` (each with two
  reworded variants) expanded into exam-style items with a topic + difficulty.
* Features per (learner, question) row: ``topic_mastery`` (learner's mastery in
  the question's topic), ``difficulty`` (authored), ``timing`` (a seeded proxy
  for how rushed the answer was; more time pressure → worse), and ``coverage``
  (fraction of the topic the learner has studied). These are exactly the four
  signals the plan calls out.
* TRUE data-generating process: outcome ~ Bernoulli(sigmoid(w*·features + b*))
  for fixed "true" weights the model does not see; each answer is a seeded draw.
* Model under test: a plain logistic regression trained by batch gradient
  descent on a TRAIN split of learners+questions, then evaluated on a disjoint
  HELD-OUT split.
* NO-LEAKAGE SPLIT: we hold out whole *concepts*, so neither paraphrase of a
  test concept is ever seen in training — a stricter split than row-random.
* Reported: accuracy on held-out questions (the headline), plus AUC and the
  majority-class baseline it must beat, and a stated ACCURACY_CUT gate.

Stdlib only; no build required.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
HELDOUT = os.path.join(HERE, "heldout.jsonl")

DEFAULT_LEARNERS = 120
# Fraction of CONCEPTS held out for the test split (whole concepts, so both
# paraphrases of a test concept stay out of training — no wording leakage).
TEST_FRACTION = 0.34
# Headline gate: the performance model must clear this accuracy on held-out
# questions AND beat the majority-class baseline. Stated up front, not tuned.
ACCURACY_CUT = 0.70

# The TRUE weights the DGP uses (the model never sees these). Order matches
# _FEATURES. Positive mastery/coverage help; difficulty and time-pressure hurt.
_TRUE_W = {
    "topic_mastery": 3.4,
    "difficulty": -3.0,
    "timing": -1.4,
    "coverage": 1.2,
}
_TRUE_B = 0.15

_FEATURES = ("topic_mastery", "difficulty", "timing", "coverage")


def _sigmoid(x: float) -> float:
    if x < -60:
        return 0.0
    if x > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def load_heldout(path: str = HELDOUT) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def build_rows(seed: int, learners: int, heldout: list[dict]) -> list[dict]:
    """Generate the (learner, question) feature rows + seeded true outcomes.

    Each row carries its ``concept_id`` so the split can hold out whole
    concepts. Deterministic given ``seed``.
    """
    rng = random.Random(seed)
    topics = sorted({item["topic"] for item in heldout})

    # Per-learner latent mastery in each topic (0..1), plus a study-coverage
    # fraction per topic. Sampled once, in a stable order for a given seed.
    learner_mastery: list[dict[str, float]] = []
    learner_coverage: list[dict[str, float]] = []
    for _ in range(learners):
        base = rng.betavariate(5, 4)  # overall ability
        learner_mastery.append(
            {t: max(0.0, min(1.0, base + rng.gauss(0, 0.12))) for t in topics}
        )
        learner_coverage.append(
            {t: rng.betavariate(4, 3) for t in topics}
        )

    rows: list[dict] = []
    for item in heldout:
        cid = item["concept_id"]
        topic = item["topic"]
        difficulty = float(item["difficulty"])
        for variant in ("question_a", "question_b"):
            for li in range(learners):
                mastery = learner_mastery[li][topic]
                coverage = learner_coverage[li][topic]
                # Seeded timing proxy in [0,1]: higher = more rushed / worse.
                timing = rng.betavariate(2, 5)
                feats = {
                    "topic_mastery": mastery,
                    "difficulty": difficulty,
                    "timing": timing,
                    "coverage": coverage,
                }
                z = _TRUE_B + sum(_TRUE_W[f] * feats[f] for f in _FEATURES)
                true_p = _sigmoid(z)
                outcome = 1 if rng.random() < true_p else 0
                rows.append(
                    {
                        "concept_id": cid,
                        "topic": topic,
                        "variant": variant,
                        "features": feats,
                        "outcome": outcome,
                    }
                )
    return rows


def split_by_concept(rows: list[dict], heldout: list[dict], seed: int,
                     test_fraction: float = TEST_FRACTION) -> tuple[list, list]:
    """Hold out whole concepts (both paraphrases) for the test split."""
    rng = random.Random(seed + 7919)  # distinct stream from the DGP
    cids = [item["concept_id"] for item in heldout]
    rng.shuffle(cids)
    n_test = max(1, round(len(cids) * test_fraction))
    test_cids = set(cids[:n_test])
    train = [r for r in rows if r["concept_id"] not in test_cids]
    test = [r for r in rows if r["concept_id"] in test_cids]
    return train, test


def _standardize(rows: list[dict]) -> tuple[dict, dict]:
    """Per-feature mean/std over TRAIN only (avoids test leakage)."""
    means, stds = {}, {}
    n = len(rows)
    for f in _FEATURES:
        xs = [r["features"][f] for r in rows]
        mu = sum(xs) / n
        var = sum((x - mu) ** 2 for x in xs) / n
        means[f] = mu
        stds[f] = math.sqrt(var) or 1.0
    return means, stds


def _vec(row: dict, means: dict, stds: dict) -> list[float]:
    return [(row["features"][f] - means[f]) / stds[f] for f in _FEATURES]


def train_logreg(train: list[dict], epochs: int = 400, lr: float = 0.3
                 ) -> tuple[list[float], float, dict, dict]:
    """Batch gradient-descent logistic regression on standardized features."""
    means, stds = _standardize(train)
    X = [_vec(r, means, stds) for r in train]
    y = [r["outcome"] for r in train]
    n = len(X)
    dim = len(_FEATURES)
    w = [0.0] * dim
    b = 0.0
    for _ in range(epochs):
        gw = [0.0] * dim
        gb = 0.0
        for xi, yi in zip(X, y):
            p = _sigmoid(b + sum(w[j] * xi[j] for j in range(dim)))
            err = p - yi
            for j in range(dim):
                gw[j] += err * xi[j]
            gb += err
        for j in range(dim):
            w[j] -= lr * gw[j] / n
        b -= lr * gb / n
    return w, b, means, stds


def predict(row: dict, w: list[float], b: float, means: dict, stds: dict
            ) -> float:
    xi = _vec(row, means, stds)
    return _sigmoid(b + sum(w[j] * xi[j] for j in range(len(w))))


def _auc(scores: list[float], labels: list[int]) -> float:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    sum_pos = sum(ranks[i] for i, y in enumerate(labels) if y == 1)
    n_pos, n_neg = len(pos), len(neg)
    u = sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def run(seed: int = 0, learners: int = DEFAULT_LEARNERS,
        heldout_path: str = HELDOUT, simulated: bool = True) -> dict:
    heldout = load_heldout(heldout_path)
    rows = build_rows(seed, learners, heldout)
    train, test = split_by_concept(rows, heldout, seed)

    w, b, means, stds = train_logreg(train)

    test_scores = [predict(r, w, b, means, stds) for r in test]
    test_labels = [r["outcome"] for r in test]
    n = len(test)
    acc = sum(1 for s, y in zip(test_scores, test_labels)
              if (s >= 0.5) == bool(y)) / n
    auc = _auc(test_scores, test_labels)

    # Majority-class baseline computed on TRAIN, scored on TEST (honest: the
    # model must beat "always guess the training-majority outcome").
    train_pos = sum(r["outcome"] for r in train) / len(train)
    majority = 1 if train_pos >= 0.5 else 0
    baseline_acc = sum(1 for y in test_labels if y == majority) / n

    beats_baseline = acc > baseline_acc
    gate_pass = (acc >= ACCURACY_CUT) and beats_baseline

    n_test_concepts = len({r["concept_id"] for r in test})
    return {
        "seed": seed,
        "learners": learners,
        "simulated": simulated,
        "features": list(_FEATURES),
        "concepts_total": len(heldout),
        "concepts_held_out": n_test_concepts,
        "train_rows": len(train),
        "test_rows": n,
        "test_base_rate": sum(test_labels) / n,
        "accuracy": acc,
        "auc": auc,
        "majority_baseline_acc": baseline_acc,
        "beats_baseline": beats_baseline,
        "accuracy_cut": ACCURACY_CUT,
        "gate_pass": gate_pass,
        "learned_weights": dict(zip(_FEATURES, w)),
        "learned_bias": b,
    }


def _fmt(m: dict) -> str:
    tag = ("  [SIMULATED — not validated against real exam data]"
           if m["simulated"] else "  [REAL revlog]")
    lines = [
        "CFA performance-model accuracy — held-out exam-style questions" + tag,
        "-" * 68,
        f"seed                 : {m['seed']}",
        f"learners             : {m['learners']}",
        f"features             : {', '.join(m['features'])}",
        f"concepts (total)     : {m['concepts_total']}",
        f"concepts held out    : {m['concepts_held_out']}  "
        f"(whole concepts — no paraphrase leakage)",
        f"train rows           : {m['train_rows']}",
        f"held-out test rows   : {m['test_rows']}",
        f"test base rate       : {m['test_base_rate']:.4f}",
        "",
        f"ACCURACY (held-out)  : {m['accuracy']:.4f}   <-- headline",
        f"AUC (ROC)            : {m['auc']:.4f}",
        f"majority baseline    : {m['majority_baseline_acc']:.4f}",
        f"beats baseline       : {m['beats_baseline']}",
        "",
        f"gate: accuracy >= {m['accuracy_cut']:.2f} AND beats baseline"
        f"  ->  {'PASS' if m['gate_pass'] else 'FAIL'}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="A4 performance-model accuracy on held-out questions")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--learners", type=int, default=DEFAULT_LEARNERS)
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    ap.add_argument("--heldout", default=HELDOUT)
    args = ap.parse_args(argv)
    m = run(seed=args.seed, learners=args.learners, heldout_path=args.heldout)
    if args.json:
        print(json.dumps(m, indent=2))
    else:
        print(_fmt(m))
    # Exit non-zero only if the model fails its own stated gate — this is a
    # model-quality bar, and (being a simulation) it should comfortably pass.
    return 0 if m["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
