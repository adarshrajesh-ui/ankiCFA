"""ReadinessModel — map performance + coverage to a configurable scale.

Supports two exam families:
  - pass_fail: point = P(pass)
  - scaled:    point = scaled score in [scale_min, scale_max]
Both carry a range and a confidence. Never emits a number when abstaining.
"""

from __future__ import annotations

import math
from typing import List

from .config import ExamConfig
from .data import QuestionResult, ReviewRecord, graded_review_count
from .giveup import GiveUpRule
from .performance import PerformanceModel
from .score import Score


def _normal_cdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return 1.0 if x <= mu else 0.0
    return 0.5 * (1.0 + math.erf((mu - x) / (sigma * math.sqrt(2.0))))


class ReadinessModel:
    def __init__(self, config: ExamConfig):
        self.config = config

    def score(
        self,
        reviews: List[ReviewRecord],
        questions: List[QuestionResult],
        coverage_pct: float,
        at_ts: float,
        updated_at: str,
    ) -> Score:
        decision = GiveUpRule(self.config).evaluate(
            graded_review_count(reviews), coverage_pct
        )
        if decision.abstain:
            return Score(
                point=None,
                range=None,
                coverage_pct=coverage_pct,
                confidence=0.0,
                updated_at=updated_at,
                reasons=decision.reasons,
                abstain=True,
            )
        perf = PerformanceModel(self.config).score(
            reviews, questions, coverage_pct, at_ts, updated_at
        )
        p = perf.point
        p_lo, p_hi = perf.range
        cfg = self.config
        # Confidence reflects both coverage and the width of the performance band.
        band_conf = 1.0 - min(1.0, (p_hi - p_lo))
        confidence = perf.confidence * band_conf

        if cfg.scale_type == "pass_fail":
            # Treat performance band as +-1 sigma around the point.
            sigma = max(1e-6, (p_hi - p_lo) / 2.0)
            p_pass = _normal_cdf(cfg.pass_threshold, p, sigma)
            lo = _normal_cdf(cfg.pass_threshold, p_hi, sigma)
            hi = _normal_cdf(cfg.pass_threshold, p_lo, sigma)
            point = p_pass
            rng = (min(lo, hi), max(lo, hi))
            reasons = [
                f"P(pass) at threshold {cfg.pass_threshold}",
                f"performance point {p:.3f}",
            ]
        else:  # scaled
            def to_scale(v: float) -> float:
                return cfg.scale_min + v * (cfg.scale_max - cfg.scale_min)

            point = to_scale(p)
            rng = (to_scale(p_lo), to_scale(p_hi))
            reasons = [
                f"scaled from performance {p:.3f}",
                f"pass_threshold={cfg.pass_threshold}",
            ]

        return Score(
            point=point,
            range=rng,
            coverage_pct=coverage_pct,
            confidence=confidence,
            updated_at=updated_at,
            reasons=reasons,
            abstain=False,
        )
