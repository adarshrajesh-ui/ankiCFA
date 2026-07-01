"""Leakage check — flag duplicate / near-duplicate items across train/test.

If an item in the test set is (nearly) identical to one in the train set, any
calibration/eval number computed on it is contaminated. We use token Jaccard on
the item stem; >= threshold counts as a near-duplicate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

from .data import QuestionResult

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set:
    return set(_TOKEN.findall(text.lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union


@dataclass
class LeakageReport:
    n_train: int
    n_test: int
    # (train_index, test_index, similarity)
    duplicates: List[Tuple[int, int, float]] = field(default_factory=list)

    @property
    def has_leakage(self) -> bool:
        return bool(self.duplicates)

    @property
    def leaked_test_count(self) -> int:
        return len({t for _, t, _ in self.duplicates})


def check_leakage(
    train: Sequence[QuestionResult],
    test: Sequence[QuestionResult],
    threshold: float = 0.85,
) -> LeakageReport:
    dups: List[Tuple[int, int, float]] = []
    train_stems = [q.stem for q in train]
    for ti, tq in enumerate(test):
        for ri, rstem in enumerate(train_stems):
            sim = jaccard(rstem, tq.stem)
            if sim >= threshold:
                dups.append((ri, ti, sim))
    return LeakageReport(n_train=len(train), n_test=len(test), duplicates=dups)
