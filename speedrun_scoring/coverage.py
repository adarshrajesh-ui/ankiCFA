"""CoverageMap — % of the exam outline that has sufficient study data.

A topic counts as "covered" when it has at least ``min_reviews_per_topic`` graded
reviews. Coverage is the weighted fraction of outline topics covered.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .data import ReviewRecord

_DEFAULT_OUTLINE = os.path.join(
    os.path.dirname(__file__), "fixtures", "topic_outline.txt"
)


@dataclass
class CoverageMap:
    weights: Dict[str, float]
    covered: Dict[str, bool] = field(default_factory=dict)

    @classmethod
    def load_outline(cls, path: str = _DEFAULT_OUTLINE) -> "CoverageMap":
        weights: Dict[str, float] = {}
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                topic = parts[0]
                weight = float(parts[1]) if len(parts) > 1 else 1.0
                weights[topic] = weight
        return cls(weights=weights)

    def compute(
        self, reviews: List[ReviewRecord], min_reviews_per_topic: int = 5
    ) -> float:
        """Return weighted coverage percentage in [0, 100]."""
        counts: Dict[str, int] = {}
        for r in reviews:
            if r.was_new:
                continue
            counts[r.topic] = counts.get(r.topic, 0) + 1
        self.covered = {
            t: counts.get(t, 0) >= min_reviews_per_topic for t in self.weights
        }
        total_w = sum(self.weights.values())
        if total_w <= 0:
            return 0.0
        covered_w = sum(w for t, w in self.weights.items() if self.covered[t])
        return 100.0 * covered_w / total_w

    def uncovered_topics(self) -> List[str]:
        return [t for t, ok in self.covered.items() if not ok]
