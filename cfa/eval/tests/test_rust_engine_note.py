"""A12: docs/cfa/RUST_ENGINE_NOTE.md must not drift from the Rust engine.

Stdlib only (no cargo build): count the ``#[test]`` / ``#[tokio::test]``
attributes in the three CFA Rust files (exam-queue tests in ``service/mod.rs``
are the ones whose test name contains ``exam_queue``), then assert the note
states each per-RPC count, the correct grand total, all three RPC names, and
that both new fork-only Rust files are cited. If someone adds a Rust test but
forgets the doc, this goes red — same guard style as ``test_model_docs.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
NOTE = REPO / "docs" / "cfa" / "RUST_ENGINE_NOTE.md"
RSLIB = REPO / "rslib" / "src" / "scheduler"

SERVICE = RSLIB / "service" / "mod.rs"
DEADLINE = RSLIB / "cfa_deadline.rs"
SCORES = RSLIB / "cfa_scores.rs"

_TEST_ATTR = re.compile(r"#\[(?:tokio::)?test\]")
# A test attr line is followed (allowing an async keyword) by `fn <name>(`.
_TEST_FN = re.compile(
    r"#\[(?:tokio::)?test\]\s*(?:async\s+)?fn\s+(\w+)\s*\(", re.DOTALL
)


def _read(p: Path) -> str:
    assert p.exists(), f"missing source {p}"
    return p.read_text(encoding="utf-8")


def _note() -> str:
    assert NOTE.exists(), f"missing doc {NOTE}"
    return NOTE.read_text(encoding="utf-8")


def _all_test_names(p: Path) -> list[str]:
    return _TEST_FN.findall(_read(p))


def _count_attrs(p: Path) -> int:
    return len(_TEST_ATTR.findall(_read(p)))


def _exam_queue_tests() -> list[str]:
    return [n for n in _all_test_names(SERVICE) if "exam_queue" in n]


# --- authoritative counts, read from source at test time -------------------


def test_exam_queue_test_count_matches_doc() -> None:
    n = len(_exam_queue_tests())
    assert n == 11, f"expected 11 exam_queue tests in service/mod.rs, found {n}"
    assert re.search(rf"{n}\s+(?:exam-queue\s+)?(?:unit\s+)?tests?", _note()), (
        f"RUST_ENGINE_NOTE.md must state {n} exam-queue tests"
    )


def test_deadline_test_count_matches_doc() -> None:
    n = _count_attrs(DEADLINE)
    # Every test attr in this file is a test fn (no non-test macros collide).
    assert n == 10, f"expected 10 tests in cfa_deadline.rs, found {n}"
    assert re.search(rf"{n}\s+(?:tests?|in `cfa_deadline\.rs`)", _note())
    assert "10 tests" in _note() or "10 in `cfa_deadline.rs`" in _note()


def test_scores_test_count_matches_doc() -> None:
    n = _count_attrs(SCORES)
    assert n == 3, f"expected 3 tests in cfa_scores.rs, found {n}"
    assert "3 in `cfa_scores.rs`" in _note() or "3 tests" in _note()


def test_grand_total_matches_doc() -> None:
    total = len(_exam_queue_tests()) + _count_attrs(DEADLINE) + _count_attrs(SCORES)
    assert total == 24, f"expected 24 CFA Rust tests, found {total}"
    assert "24 passed" in _note() and "24 tests total" in _note()


def test_all_three_rpcs_named() -> None:
    text = _note()
    for rpc in ("BuildExamQueue", "DeadlineRetention", "ComputeCfaScores"):
        assert rpc in text, f"RPC {rpc} not documented in the note"


def test_new_fork_only_rust_files_cited() -> None:
    text = _note()
    for f in ("cfa_deadline.rs", "cfa_scores.rs"):
        assert f in text, f"new fork-only file {f} not cited in the note"
    # Merge-difficulty verdict must be present and low.
    assert "future-merge difficulty: **low**" in text
