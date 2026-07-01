"""Explicit, configurable abstention rule.

A made-up readiness number is an automatic fail, so when data is insufficient we
ABSTAIN loudly with reasons rather than emitting a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .config import ExamConfig


@dataclass
class GiveUpDecision:
    abstain: bool
    reasons: List[str] = field(default_factory=list)
    graded_reviews: int = 0
    coverage_pct: float = 0.0


class GiveUpRule:
    """Default: abstain if graded_reviews < 200 OR coverage < 50%."""

    def __init__(self, config: ExamConfig):
        self.config = config

    def evaluate(self, graded_reviews: int, coverage_pct: float) -> GiveUpDecision:
        reasons: List[str] = []
        if graded_reviews < self.config.min_graded_reviews:
            reasons.append(
                f"insufficient graded reviews: {graded_reviews} < "
                f"{self.config.min_graded_reviews}"
            )
        if coverage_pct < self.config.min_coverage_pct:
            reasons.append(
                f"insufficient coverage: {coverage_pct:.1f}% < "
                f"{self.config.min_coverage_pct:.1f}%"
            )
        return GiveUpDecision(
            abstain=bool(reasons),
            reasons=reasons,
            graded_reviews=graded_reviews,
            coverage_pct=coverage_pct,
        )
