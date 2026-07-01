"""MemoryModel — per-card recall probability from review history.

FSRS-style retrievability with a stability estimated from the grade sequence.
Point estimate + interval (width shrinks as review count grows).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import ExamConfig
from .data import (
    ReviewRecord,
    graded_review_count,
    retrievability,
    _initial_stability,
    _next_stability,
)
from .giveup import GiveUpRule
from .score import Score


@dataclass
class CardMemory:
    card_id: int
    topic: str
    stability: float
    last_ts: float
    n_reviews: int

    def recall(self, at_ts: float) -> float:
        return retrievability(max(0.0, at_ts - self.last_ts), self.stability)

    def recall_interval(self, at_ts: float) -> tuple[float, float]:
        """Uncertainty band that narrows with more reviews."""
        point = self.recall(at_ts)
        half = min(0.45, 0.6 / math.sqrt(self.n_reviews + 1))
        lo = max(0.0, point - half)
        hi = min(1.0, point + half)
        return lo, hi


class MemoryModel:
    def __init__(self, config: ExamConfig):
        self.config = config

    def fit_card(self, reviews: List[ReviewRecord]) -> Optional[CardMemory]:
        """Estimate stability for one card from its (time-ordered) reviews."""
        if not reviews:
            return None
        rs = sorted(reviews, key=lambda r: r.ts)
        stability = _initial_stability(rs[0].grade)
        last_ts = rs[0].ts
        for rec in rs[1:]:
            elapsed = max(0.0, rec.ts - last_ts)
            r = retrievability(elapsed, stability)
            stability = _next_stability(stability, rec.grade, r)
            last_ts = rec.ts
        return CardMemory(
            card_id=rs[0].card_id,
            topic=rs[0].topic,
            stability=stability,
            last_ts=last_ts,
            n_reviews=len(rs),
        )

    def fit(self, reviews: List[ReviewRecord]) -> Dict[int, CardMemory]:
        by_card: Dict[int, List[ReviewRecord]] = {}
        for rec in reviews:
            by_card.setdefault(rec.card_id, []).append(rec)
        out: Dict[int, CardMemory] = {}
        for cid, recs in by_card.items():
            cm = self.fit_card(recs)
            if cm is not None:
                out[cid] = cm
        return out

    def topic_mastery(
        self, cards: Dict[int, CardMemory], at_ts: float
    ) -> Dict[str, float]:
        """Mean recall per topic (drives the performance model)."""
        acc: Dict[str, List[float]] = {}
        for cm in cards.values():
            acc.setdefault(cm.topic, []).append(cm.recall(at_ts))
        return {t: (sum(v) / len(v)) for t, v in acc.items() if v}

    def score(
        self,
        reviews: List[ReviewRecord],
        coverage_pct: float,
        at_ts: float,
        updated_at: str,
    ) -> Score:
        """Aggregate Memory score (mean recall across all cards)."""
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
        cards = self.fit(reviews)
        points = [cm.recall(at_ts) for cm in cards.values()]
        los, his = zip(*(cm.recall_interval(at_ts) for cm in cards.values()))
        point = sum(points) / len(points)
        rng = (sum(los) / len(los), sum(his) / len(his))
        confidence = min(1.0, len(cards) / 100.0) * (coverage_pct / 100.0)
        return Score(
            point=point,
            range=rng,
            coverage_pct=coverage_pct,
            confidence=confidence,
            updated_at=updated_at,
            reasons=[f"{len(cards)} cards modelled"],
            abstain=False,
        )
