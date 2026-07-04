"""A11: the MODEL-*.md score-mapping docs must not drift from the code.

Stdlib only (no anki import / no build): parse the numeric constants out of the
Python reference ``pylib/anki/cfa.py`` and assert each is stated verbatim in the
matching ``docs/cfa/MODEL-*.md``. If someone changes a threshold in code, the
doc test goes red until the doc is updated too.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "pylib" / "anki" / "cfa.py"
DOCS = REPO / "docs" / "cfa"


def _src() -> str:
    return SRC.read_text(encoding="utf-8")


def _const(name: str) -> str:
    """Return the RHS literal of a top-level ``NAME = <literal>`` assignment."""
    m = re.search(rf"^{name}\s*=\s*([^\n#]+)", _src(), re.MULTILINE)
    assert m, f"constant {name} not found in {SRC}"
    return m.group(1).strip()


def _doc(name: str) -> str:
    p = DOCS / name
    assert p.exists(), f"missing doc {p}"
    return p.read_text(encoding="utf-8")


def test_all_three_docs_exist() -> None:
    for name in ("MODEL-MEMORY.md", "MODEL-PERFORMANCE.md", "MODEL-READINESS.md"):
        text = _doc(name)
        # Every doc must carry the three required sections + honesty framing.
        assert "## Method" in text
        assert "## Range" in text
        assert "## Give-up rule" in text.replace(
            "Give-up rule (enforced)", "Give-up rule"
        )


def test_memory_doc_matches_constants() -> None:
    text = _doc("MODEL-MEMORY.md")
    assert _const("MIN_GRADED_REVIEWS") == "200"
    assert "200" in text
    assert _const("MIN_TOPIC_COVERAGE") == "0.50"
    assert "50 %" in text or "50%" in text
    # 10 canonical topics is the fixed coverage denominator.
    assert "10" in text


def test_performance_doc_matches_constants() -> None:
    text = _doc("MODEL-PERFORMANCE.md")
    assert _const("MIN_FIRST_EXPOSURES") == "30"
    assert "30" in text
    assert _const("_CORRECT_EASE") == "2"
    assert "ease >= 2" in text
    # Wilson 95% interval is the stated range shape.
    assert "Wilson" in text and "95" in text


def test_readiness_doc_matches_constants() -> None:
    text = _doc("MODEL-READINESS.md")
    assert _const("_MPS") == "0.65"
    assert "0.65" in text
    assert _const("_READINESS_K") == "8.0"
    assert "8.0" in text
    assert _const("_READINESS_MARGIN") == "0.15"
    assert "0.15" in text
    # Guess rate on a 3-choice item = 1/3.
    assert _const("_GUESS_RATE") == "1.0 / 3.0"
    assert "1/3" in text or "3-choice" in text
    # Standing honesty caveat must be quoted verbatim.
    label = _const("READINESS_LABEL").strip('"')
    assert label == "not validated against real exam data"
    assert label in text


def test_docs_name_the_source_functions() -> None:
    # Each doc should point at the Python reference + the shared Rust RPC.
    for name in ("MODEL-MEMORY.md", "MODEL-PERFORMANCE.md", "MODEL-READINESS.md"):
        text = _doc(name)
        assert "cfa_scores.rs" in text
        assert "compute_cfa_scores" in text
    assert "_py_memory_score" in _doc("MODEL-MEMORY.md")
    assert "_py_performance_score" in _doc("MODEL-PERFORMANCE.md")
    assert "_py_readiness_score" in _doc("MODEL-READINESS.md")
