"""Honest measurement layer for exam-readiness speedrun.

Standalone, deterministic, no Anki / network / AI dependency. Operates on a
defined data interface (ReviewRecord / QuestionResult) plus synthetic fixtures.

Three SEPARATE scores, each a range, plus a strict abstain rule:
  - MemoryModel      -> recall probability per card (FSRS-style retrievability)
  - PerformanceModel -> P(correct on a NEW question) (+ paraphrase-gap metric)
  - ReadinessModel   -> configurable-scale readiness (pass/fail or scaled)
"""

from .config import ExamConfig, PASS_FAIL_EXAMPLE, SCALED_EXAMPLE
from .data import ReviewRecord, QuestionResult, SyntheticFixture, generate_fixture
from .score import Score
from .memory import MemoryModel
from .performance import PerformanceModel, paraphrase_gap
from .readiness import ReadinessModel
from .giveup import GiveUpRule, GiveUpDecision
from .coverage import CoverageMap
from .calibration import CalibrationReport, calibrate
from .leakage import LeakageReport, check_leakage

__all__ = [
    "ExamConfig",
    "PASS_FAIL_EXAMPLE",
    "SCALED_EXAMPLE",
    "ReviewRecord",
    "QuestionResult",
    "SyntheticFixture",
    "generate_fixture",
    "Score",
    "MemoryModel",
    "PerformanceModel",
    "paraphrase_gap",
    "ReadinessModel",
    "GiveUpRule",
    "GiveUpDecision",
    "CoverageMap",
    "CalibrationReport",
    "calibrate",
    "LeakageReport",
    "check_leakage",
]
