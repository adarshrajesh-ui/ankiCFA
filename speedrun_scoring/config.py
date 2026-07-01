"""Exam configuration. The scale lives HERE, never hardcoded in model logic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExamConfig:
    """Exam-agnostic scoring configuration.

    scale_type:
      - "pass_fail": readiness reports P(pass); ``pass_threshold`` is the
        performance level considered "passing".
      - "scaled": readiness maps performance -> [scale_min, scale_max];
        ``pass_threshold`` is the passing scaled score.
    """

    name: str
    scale_type: str  # "pass_fail" | "scaled"
    scale_min: float
    scale_max: float
    pass_threshold: float
    # Give-up (abstain) thresholds — configurable, defaults per objective.
    min_graded_reviews: int = 200
    min_coverage_pct: float = 50.0
    # Fraction of raw card recall that transfers to a reworded question.
    # < 1.0 means questions are harder than flashcards (the paraphrase gap).
    paraphrase_transfer: float = 0.85

    def __post_init__(self) -> None:
        if self.scale_type not in ("pass_fail", "scaled"):
            raise ValueError(f"unknown scale_type: {self.scale_type}")
        if self.scale_max <= self.scale_min:
            raise ValueError("scale_max must exceed scale_min")
        if not (0.0 < self.paraphrase_transfer <= 1.0):
            raise ValueError("paraphrase_transfer must be in (0, 1]")


# Two shipped examples so nothing about a specific exam is baked into logic.
PASS_FAIL_EXAMPLE = ExamConfig(
    name="EXAMPLE-PASS-FAIL",
    scale_type="pass_fail",
    scale_min=0.0,
    scale_max=1.0,
    pass_threshold=0.65,
)

SCALED_EXAMPLE = ExamConfig(
    name="EXAMPLE-SCALED",
    scale_type="scaled",
    scale_min=118.0,
    scale_max=132.0,
    pass_threshold=125.0,
)
