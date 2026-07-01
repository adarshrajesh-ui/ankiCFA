"""PerformanceModel — P(correct on a NEW question).

Distinct from memory: knowing a flashcard cold does not guarantee answering a
reworded exam question. The paraphrase-gap metric quantifies exactly that gap so
the two scores can (and do) differ.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

from .config import ExamConfig
from .data import QuestionResult, ReviewRecord, graded_review_count
from .giveup import GiveUpRule
from .memory import MemoryModel, CardMemory
from .score import Score


def paraphrase_gap(
    topic_mastery: Dict[str, float], questions: List[QuestionResult]
) -> float:
    """mean card recall - mean reworded-question accuracy over shared topics.

    Positive => questions are harder than flashcards (the usual case).
    """
    by_topic: Dict[str, List[QuestionResult]] = {}
    for q in questions:
        by_topic.setdefault(q.topic, []).append(q)
    shared = [t for t in by_topic if t in topic_mastery]
    if not shared:
        return float("nan")
    recall_vals = [topic_mastery[t] for t in shared]
    acc_vals = [
        sum(1 for q in by_topic[t] if q.correct) / len(by_topic[t]) for t in shared
    ]
    return sum(recall_vals) / len(recall_vals) - sum(acc_vals) / len(acc_vals)


class PerformanceModel:
    def __init__(self, config: ExamConfig):
        self.config = config

    def predict_question(self, mastery: float, difficulty: float) -> float:
        """P(correct) for a NEW question of given difficulty in a topic.

        Applies the configured paraphrase transfer, so performance < mastery.
        """
        p = mastery * self.config.paraphrase_transfer * (1.0 - 0.4 * difficulty)
        return min(1.0, max(0.0, p))

    def _mean_performance(
        self, topic_mastery: Dict[str, float], questions: List[QuestionResult]
    ) -> float:
        by_topic: Dict[str, List[QuestionResult]] = {}
        for q in questions:
            by_topic.setdefault(q.topic, []).append(q)
        preds = []
        for t, qs in by_topic.items():
            m = topic_mastery.get(t)
            if m is None:
                continue
            for q in qs:
                preds.append(self.predict_question(m, q.difficulty))
        if not preds:
            return float("nan")
        return sum(preds) / len(preds)

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
        mem = MemoryModel(self.config)
        cards = mem.fit(reviews)
        topic_mastery = mem.topic_mastery(cards, at_ts)
        point = self._mean_performance(topic_mastery, questions)
        gap = paraphrase_gap(topic_mastery, questions)
        # Range widens with the (empirical) paraphrase-gap uncertainty and
        # narrows as questions/topics accumulate.
        n_q = len(questions)
        half = min(0.4, 0.5 / math.sqrt(max(1, n_q)) + 0.3 * abs(gap))
        rng = (max(0.0, point - half), min(1.0, point + half))
        confidence = min(1.0, len(topic_mastery) / len(self._topics(questions))) * (
            coverage_pct / 100.0
        )
        return Score(
            point=point,
            range=rng,
            coverage_pct=coverage_pct,
            confidence=confidence,
            updated_at=updated_at,
            reasons=[
                f"paraphrase_gap={gap:.3f}",
                f"{n_q} questions across {len(topic_mastery)} topics",
            ],
            abstain=False,
        )

    @staticmethod
    def _topics(questions: List[QuestionResult]) -> set:
        return {q.topic for q in questions}
