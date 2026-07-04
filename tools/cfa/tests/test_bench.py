# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for A9 — the 50k-card latency benchmark.

The statistics helpers (percentile, Stat, report formatting) are pure-Python
and tested directly. The deck-build and per-op passes need the real built
backend (``out/pylib`` on the path, as ``just cfa-tools-test`` provides), so
they run on a tiny throwaway collection and assert the shape/plausibility of
the measured samples rather than absolute timings.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import tempfile

import pytest

REPO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
BENCH_PATH = os.path.join(REPO, "tools", "cfa", "bench.py")


def _load():
    import sys

    spec = importlib.util.spec_from_file_location("cfa_bench", BENCH_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass module-dict introspection works under
    # ``from __future__ import annotations``.
    sys.modules["cfa_bench"] = mod
    spec.loader.exec_module(mod)
    return mod


B = _load()

# Whether the real backend is importable in this environment.
try:
    from anki.collection import Collection  # noqa: F401

    _HAVE_BACKEND = True
except Exception:
    _HAVE_BACKEND = False

needs_backend = pytest.mark.skipif(
    not _HAVE_BACKEND, reason="built pylib backend not on path"
)


# --- pure statistics ---------------------------------------------------------


def test_percentile_nearest_rank():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert B._percentile(vals, 50) == 5.0
    assert B._percentile(vals, 95) == 10.0
    assert B._percentile(vals, 100) == 10.0
    # single element and empty
    assert B._percentile([42.0], 95) == 42.0
    assert math.isnan(B._percentile([], 50))


def test_stat_summary():
    s = B.Stat("op", samples_ms=[10.0, 20.0, 30.0, 40.0, 100.0])
    assert s.n == 5
    assert s.p50 == 30.0
    assert s.worst == 100.0
    # p95 is the largest by nearest-rank on 5 samples
    assert s.p95 == 100.0
    d = s.as_dict()
    assert d["worst_ms"] == 100.0
    # JSON serializable
    json.dumps(d)


def test_empty_stat_as_dict():
    s = B.Stat("op")
    d = s.as_dict()
    assert d["n"] == 0
    assert d["p50_ms"] is None and d["worst_ms"] is None


def test_format_report_marks_blocked_and_skipped():
    stats = [
        B.Stat("next-card", samples_ms=[0.1, 0.2, 0.3]),
        B.Stat("sync", note="BLOCKED: server down"),
    ]
    meta = {
        "cards": 600,
        "studied": 210,
        "reps": 40,
        "build_s": 0.1,
        "machine": "test",
    }
    txt = B.format_report(stats, meta)
    assert "p50 (ms)" in txt and "worst (ms)" in txt
    assert "next-card" in txt
    assert "BLOCKED: server down" in txt


# --- real-backend passes -----------------------------------------------------


@needs_backend
def test_build_deck_shape():
    from anki.collection import Collection

    d = tempfile.mkdtemp(prefix="cfa-bench-test-")
    col = Collection(os.path.join(d, "c.anki2"))
    try:
        B.build_deck(col, 200)
        assert col.card_count() == 200
        # roughly STUDIED_FRACTION are review cards with graded revlog
        # (ease > 0 excludes set_due_date's manual reschedule entries)
        rev = col.db.scalar("select count(*) from revlog where ease > 0")
        expected = int(200 * B.STUDIED_FRACTION) * B.REVIEWS_EACH
        assert rev == expected
        # every card carries a canonical topic tag
        from anki import cfa

        for topic in cfa.CANONICAL_TOPICS:
            assert (
                col.db.scalar(
                    "select count(*) from notes where tags like ?", f"%{topic}::r1%"
                )
                > 0
            )
    finally:
        col.close()


@needs_backend
def test_review_loop_produces_samples():
    from anki.collection import Collection

    d = tempfile.mkdtemp(prefix="cfa-bench-test-")
    col = Collection(os.path.join(d, "c.anki2"))
    try:
        B.build_deck(col, 300)
        nxt, ack = B.bench_review_loop(col, 40)
        assert nxt.n == 40
        assert ack.n >= 39  # one fewer only if the queue drains
        assert all(x >= 0 for x in nxt.samples_ms + ack.samples_ms)
    finally:
        col.close()


@needs_backend
def test_dashboard_cold_and_warm():
    from anki.collection import Collection

    d = tempfile.mkdtemp(prefix="cfa-bench-test-")
    col = Collection(os.path.join(d, "c.anki2"))
    try:
        B.build_deck(col, 300)
        first, refresh = B.bench_dashboard(col, 5)
        assert first.n == 1
        assert refresh.n == 5
        assert first.worst > 0 and refresh.worst > 0
    finally:
        col.close()


@needs_backend
def test_run_benchmark_smoke_no_sync():
    stats, meta = B.run_benchmark(n_cards=200, reps=30, do_sync=False, sync_reps=0)
    by_name = {s.name: s for s in stats}
    assert by_name["next-card"].n == 30
    assert by_name["answerCard ack"].n >= 29
    assert by_name["dashboard first load"].n == 1
    assert by_name["dashboard refresh"].n >= 3
    # sync explicitly skipped, not fabricated
    assert by_name["sync"].n == 0
    assert "SKIPPED" in by_name["sync"].note
    assert meta["cards"] == 200


@needs_backend
def test_main_smoke_exits_zero(capsys):
    rc = B.main(["--smoke"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "50k-card latency benchmark" in out
    assert "p50 (ms)" in out
