"""Headless eval: print calibration + paraphrase-gap numbers on the fixtures.

Deterministic. No network, no AI. Exits 0 on success.

    python -m speedrun_scoring.eval
"""

from __future__ import annotations

import sys

from .calibration import calibrate
from .config import PASS_FAIL_EXAMPLE, SCALED_EXAMPLE
from .coverage import CoverageMap
from .data import generate_fixture, graded_review_count
from .memory import MemoryModel
from .performance import PerformanceModel, paraphrase_gap
from .readiness import ReadinessModel

_STAMP = "2026-07-01T00:00:00Z"  # injected clock -> deterministic output


def _fmt_score(name, s):
    if s.abstain:
        return f"{name:<12} ABSTAIN  reasons={s.reasons}"
    lo, hi = s.range
    return (
        f"{name:<12} point={s.point:.3f}  range=[{lo:.3f},{hi:.3f}]  "
        f"conf={s.confidence:.3f}  cov={s.coverage_pct:.1f}%"
    )


def run() -> int:
    fx = generate_fixture(seed=7)
    at_ts = max(r.ts for r in fx.reviews) + 1.0

    cov = CoverageMap.load_outline()
    coverage_pct = cov.compute(fx.reviews)

    print("=== speedrun_scoring headless eval ===")
    print(f"reviews={len(fx.reviews)}  graded={graded_review_count(fx.reviews)}  "
          f"questions={len(fx.questions)}  coverage={coverage_pct:.1f}%")

    # Calibration (held-out) on the pass/fail config.
    report = calibrate(PASS_FAIL_EXAMPLE, fx.reviews)
    print("\n-- calibration (held-out last review per card) --")
    print(f"n={report.n}  brier={report.brier:.4f}  log_loss={report.log_loss:.4f}")
    print("reliability (bin_center, mean_pred, mean_obs, count):")
    for center, mp, mo, c in report.reliability:
        print(f"  {center:.2f}  pred={mp:.3f}  obs={mo:.3f}  n={c}")

    # Paraphrase gap: memory recall vs reworded-question accuracy.
    mem = MemoryModel(PASS_FAIL_EXAMPLE)
    cards = mem.fit(fx.reviews)
    topic_mastery = mem.topic_mastery(cards, at_ts)
    gap = paraphrase_gap(topic_mastery, fx.questions)
    print("\n-- paraphrase gap (memory recall - question accuracy) --")
    print(f"gap={gap:.4f}")

    # Three separate scores, each a range.
    print("\n-- scores (pass/fail exam) --")
    print(_fmt_score("Memory", mem.score(fx.reviews, coverage_pct, at_ts, _STAMP)))
    print(_fmt_score(
        "Performance",
        PerformanceModel(PASS_FAIL_EXAMPLE).score(
            fx.reviews, fx.questions, coverage_pct, at_ts, _STAMP
        ),
    ))
    print(_fmt_score(
        "Readiness",
        ReadinessModel(PASS_FAIL_EXAMPLE).score(
            fx.reviews, fx.questions, coverage_pct, at_ts, _STAMP
        ),
    ))

    print("\n-- readiness (scaled exam) --")
    print(_fmt_score(
        "Readiness",
        ReadinessModel(SCALED_EXAMPLE).score(
            fx.reviews, fx.questions, coverage_pct, at_ts, _STAMP
        ),
    ))

    # Sanity gates so eval fails loudly if the pipeline degrades.
    ok = True
    if not (report.n > 0 and report.brier < 0.25):
        print(f"\nFAIL: calibration Brier too high or empty: {report.brier}")
        ok = False
    if not (gap > 0.0):
        print(f"\nFAIL: expected a positive paraphrase gap, got {gap}")
        ok = False
    print("\nRESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
