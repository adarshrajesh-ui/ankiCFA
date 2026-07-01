"""Data interface + deterministic synthetic fixture generator.

The fixture encodes a KNOWN latent recall process so the calibration harness has
ground truth to measure against, and an intentional paraphrase gap so Memory and
Performance provably differ.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List

# FSRS-style retrievability constants (target retention 0.9 at t == S).
FSRS_DECAY = -0.5
FSRS_FACTOR = 19.0 / 81.0


def retrievability(elapsed_days: float, stability: float) -> float:
    """Power-forgetting-curve recall probability."""
    if stability <= 0:
        return 0.0
    if elapsed_days <= 0:
        return 1.0
    return (1.0 + FSRS_FACTOR * elapsed_days / stability) ** FSRS_DECAY


@dataclass
class ReviewRecord:
    card_id: int
    topic: str
    ts: float  # days since epoch of study start
    grade: int  # 1=again(lapse), 2=hard, 3=good, 4=easy
    latency: float  # seconds
    was_new: bool

    @property
    def recalled(self) -> bool:
        return self.grade >= 2


@dataclass
class QuestionResult:
    topic: str
    difficulty: float  # 0..1
    correct: bool
    latency: float  # seconds
    stem: str = ""  # optional item text; used by the leakage check


@dataclass
class SyntheticFixture:
    reviews: List[ReviewRecord] = field(default_factory=list)
    questions: List[QuestionResult] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    # Bookkeeping so tests can assert on the generating process.
    n_cards: int = 0


def _initial_stability(grade: int) -> float:
    return {1: 0.4, 2: 1.2, 3: 3.0, 4: 8.0}[grade]


def _next_stability(stability: float, grade: int, r: float) -> float:
    """Update latent stability after a review (grade at recall level r)."""
    if grade == 1:  # lapse
        return max(0.4, stability * 0.4)
    # Larger gains when reviewed while recall was low ("desirable difficulty").
    gain = 1.0 + (grade - 1) * 0.9 * (1.0 - r)
    return stability * gain


def _sample_grade(rng: random.Random, r: float) -> int:
    """Sample a grade from a true recall probability r."""
    if rng.random() >= r:
        return 1  # failed to recall
    # Recalled: distribute across hard/good/easy by how strong recall was.
    roll = rng.random()
    if roll < 0.2:
        return 2
    if roll < 0.75:
        return 3
    return 4


def generate_fixture(
    seed: int = 0,
    n_cards: int = 120,
    n_topics: int = 6,
    reviews_per_card: int = 6,
    questions_per_topic: int = 40,
) -> SyntheticFixture:
    """Deterministic fixture. Same seed -> byte-identical output."""
    rng = random.Random(seed)
    topics = [f"topic_{i}" for i in range(n_topics)]
    fx = SyntheticFixture(topics=topics, n_cards=n_cards)

    for card_id in range(n_cards):
        topic = topics[card_id % n_topics]
        # Latent per-card stability seed (varies difficulty of cards).
        s_true = rng.uniform(0.8, 6.0)
        last_ts = 0.0
        for j in range(reviews_per_card):
            if j == 0:
                elapsed = 0.0
                r = 1.0
            else:
                # Study schedule roughly follows current stability.
                elapsed = max(0.5, s_true * rng.uniform(0.5, 1.4))
                r = retrievability(elapsed, s_true)
            ts = last_ts + elapsed
            grade = _sample_grade(rng, r) if j > 0 else rng.choice([3, 3, 4])
            latency = max(0.6, rng.gauss(6.0, 2.0))
            fx.reviews.append(
                ReviewRecord(
                    card_id=card_id,
                    topic=topic,
                    ts=ts,
                    grade=grade,
                    latency=latency,
                    was_new=(j == 0),
                )
            )
            s_true = _next_stability(s_true, grade, r)
            last_ts = ts

    # Questions: accuracy is card recall * paraphrase_transfer * difficulty term,
    # so reworded-question accuracy is genuinely lower than raw card recall.
    transfer = 0.82
    for topic in topics:
        for q in range(questions_per_topic):
            difficulty = rng.uniform(0.1, 0.9)
            # Approx topic mastery = mean recall for topic's cards right now.
            base = rng.uniform(0.55, 0.9)
            p_correct = base * transfer * (1.0 - 0.4 * difficulty)
            correct = rng.random() < p_correct
            stem = f"{topic} q{q} stem tokens {q % 7} {q % 3}"
            fx.questions.append(
                QuestionResult(
                    topic=topic,
                    difficulty=difficulty,
                    correct=correct,
                    latency=max(3.0, rng.gauss(45.0, 12.0)),
                    stem=stem,
                )
            )
    return fx


def graded_review_count(reviews: List[ReviewRecord]) -> int:
    """Reviews that were actual graded recalls (exclude first-exposure 'new')."""
    return sum(1 for r in reviews if not r.was_new)
