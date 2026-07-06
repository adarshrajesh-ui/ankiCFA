"""A14: proof/friday/RESULTS-REPORT.md must not drift from the raw evidence.

Stdlib only (no build). The consolidated report is only trustworthy if every
number in it is still backed by the evidence file it claims to summarise. This
guard, in the same style as ``test_model_docs.py`` / ``test_rust_engine_note.py``:

  * asserts the report and the updated Brainlift section exist;
  * asserts every evidence file the report cites under ``L1/`` actually exists;
  * for each headline number, asserts the *exact* string appears BOTH in the
    report AND in its source evidence file — so editing one without the other
    goes red;
  * asserts the honesty scaffolding (SIMULATED labels, the "did NOT clear their
    bar" section, the AI-off claim) is present, since a wins-only report would
    violate the honesty rule.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REPORT = REPO / "proof" / "friday" / "RESULTS-REPORT.md"
BRAINLIFT = REPO / "Brainlift.md"
L1 = REPO / "proof" / "friday" / "gnhf-speedrun" / "L1"

# (evidence filename, list of headline number strings that must appear verbatim
# in BOTH the report and that evidence file). Each string is chosen to be an
# exact substring of the source file so the guard is a true drift check.
NUMBER_SOURCES: dict[str, list[str]] = {
    "baseline-compare.txt": ["0.733", "0.933"],
    "eval-gate.txt": ["0.000"],
    "calibration.txt": ["0.2024", "0.5909", "0.0784"],
    "performance-eval.txt": ["0.7217", "0.7161", "0.6863"],
    "paraphrase-gap.txt": ["0.2583", "0.2408", "0.2767"],
    "coverage-map.txt": ["10/10", "711"],
    "ablation.txt": ["0.6435", "0.6157", "0.5626", "+0.0809"],
    "bench.txt": ["0.036"],
    "crash-robustness.txt": ["280", "4358", "0.9985"],
}

# Every evidence path the report links to (relative to L1) must exist on disk.
CITED_EVIDENCE = [
    "baseline-compare.txt",
    "eval-gate.txt",
    "calibration.txt",
    "calibration.png",
    "performance-eval.txt",
    "paraphrase-gap.txt",
    "cardgen-check.txt",
    "coverage-map.txt",
    "coverage-map.png",
    "ablation.txt",
    "bench.txt",
    "crash-robustness.txt",
    "model-docs.txt",
    "rust-engine-note.txt",
    "installer",
]


def _report() -> str:
    assert REPORT.exists(), f"missing consolidated report {REPORT}"
    return REPORT.read_text(encoding="utf-8")


def test_report_and_brainlift_section_exist() -> None:
    text = _report()
    assert "Consolidated Results Report" in text
    bl = BRAINLIFT.read_text(encoding="utf-8")
    # The A14 Brainlift update ties the thesis to measured results.
    assert "Product Validation" in bl
    assert "Memory ≠ Performance ≠ Readiness" in bl


def test_all_cited_evidence_files_exist() -> None:
    missing = [name for name in CITED_EVIDENCE if not (L1 / name).exists()]
    assert not missing, f"report cites evidence that does not exist: {missing}"


def test_headline_numbers_match_their_evidence() -> None:
    report = _report()
    for fname, numbers in NUMBER_SOURCES.items():
        src = (L1 / fname).read_text(encoding="utf-8")
        for num in numbers:
            assert num in src, f"{num} not found in evidence {fname} (drift?)"
            assert num in report, f"{num} in {fname} but missing from the report"


def test_honesty_scaffolding_present() -> None:
    text = _report()
    # SIMULATED must be labelled, the failures section must exist, and the
    # AI-off contract must be stated — a wins-only report is a fail.
    assert "SIMULATED" in text
    assert "did NOT clear their bar" in text
    assert "AI" in text and "off" in text.lower()
    # The four honest nulls / limitations must each be named.
    for token in ("UNPROVEN", "FAIL", "bottleneck", "not validated"):
        assert token in text, f"honest limitation '{token}' missing from report"


def test_every_phase_a_item_row_present() -> None:
    text = _report()
    # A1..A13 each appear as a scorecard row. Allow column-alignment padding
    # (dprint normalises the markdown table, so e.g. "| A1  |" is canonical).
    for i in range(1, 14):
        assert re.search(rf"\| A{i} +\|", text), f"scorecard row for A{i} missing"
