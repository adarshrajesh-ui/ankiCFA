"""Calibration harness — reliability curve + Brier + log-loss on held-out data.

Held-out protocol for memory: for each card with >=2 reviews, train on all but the
last review, predict recall for the last review, compare to the observed outcome
(grade >= 2 == recalled).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .config import ExamConfig
from .data import ReviewRecord
from .memory import MemoryModel


@dataclass
class CalibrationReport:
    brier: float
    log_loss: float
    n: int
    # reliability curve: list of (bin_center, mean_pred, mean_obs, count)
    reliability: List[Tuple[float, float, float, int]] = field(default_factory=list)


def brier_score(preds: List[float], obs: List[int]) -> float:
    return sum((p - o) ** 2 for p, o in zip(preds, obs)) / len(preds)


def log_loss(preds: List[float], obs: List[int], eps: float = 1e-12) -> float:
    total = 0.0
    for p, o in zip(preds, obs):
        p = min(1.0 - eps, max(eps, p))
        total += -(o * math.log(p) + (1 - o) * math.log(1.0 - p))
    return total / len(preds)


def reliability_curve(
    preds: List[float], obs: List[int], n_bins: int = 10
) -> List[Tuple[float, float, float, int]]:
    bins: List[Tuple[List[float], List[int]]] = [([], []) for _ in range(n_bins)]
    for p, o in zip(preds, obs):
        idx = min(n_bins - 1, int(p * n_bins))
        bins[idx][0].append(p)
        bins[idx][1].append(o)
    curve = []
    for i, (ps, os) in enumerate(bins):
        center = (i + 0.5) / n_bins
        if ps:
            curve.append(
                (center, sum(ps) / len(ps), sum(os) / len(os), len(ps))
            )
    return curve


def held_out_memory_predictions(
    config: ExamConfig, reviews: List[ReviewRecord]
) -> Tuple[List[float], List[int]]:
    """Train-on-prefix, predict-last for every card with >= 2 reviews."""
    model = MemoryModel(config)
    by_card: Dict[int, List[ReviewRecord]] = {}
    for r in reviews:
        by_card.setdefault(r.card_id, []).append(r)
    preds: List[float] = []
    obs: List[int] = []
    for recs in by_card.values():
        rs = sorted(recs, key=lambda r: r.ts)
        if len(rs) < 2:
            continue
        train, test = rs[:-1], rs[-1]
        cm = model.fit_card(train)
        if cm is None:
            continue
        preds.append(cm.recall(test.ts))
        obs.append(1 if test.recalled else 0)
    return preds, obs


def calibrate(
    config: ExamConfig, reviews: List[ReviewRecord], n_bins: int = 10
) -> CalibrationReport:
    preds, obs = held_out_memory_predictions(config, reviews)
    if not preds:
        return CalibrationReport(brier=float("nan"), log_loss=float("nan"), n=0)
    return CalibrationReport(
        brier=brier_score(preds, obs),
        log_loss=log_loss(preds, obs),
        n=len(preds),
        reliability=reliability_curve(preds, obs, n_bins),
    )
