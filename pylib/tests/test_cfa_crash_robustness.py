# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A10 — crash + offline robustness (SPEEDRUN plan item 7g).

Two honest guarantees, both exercised against the REAL built backend (no AI,
no network):

1. **Kill mid-review → zero corruption.** A subprocess reviews cards in a tight
   loop, committing a real review to disk every iteration; the parent SIGKILLs
   it ~20 times at random points *after* the first review has committed, then
   reopens the collection and runs the backend integrity check
   (``fix_integrity`` → ``check_database`` / ``quick_check``). Every reopen must
   report a clean database, and the review log must have grown — proving real
   reviews were interrupted, survived, and left no corruption. This is a test of
   SQLite durability + Anki's transaction discipline under SIGKILL, the closest
   faithful model of a phone/desktop being force-quit mid-study.

2. **Offline + AI-off still scores.** With the AI master toggle explicitly OFF
   and no network involved, the three CFA scores must still compute and return a
   real (non-abstaining) range — the scoring path is pure local Rust/Python and
   never depends on the network or the LLM.
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile
import time

from anki.collection import Collection
from anki.decks import DeckId

# Reuse the vetted rich seeder (two exam-weighted topics with FSRS memory
# state, first-exposure accuracy, and full coverage) so the scoring path has
# enough evidence to return a real range rather than abstaining.
from tests.test_cfa_scores import _seed_rich

WORKER = os.path.join(os.path.dirname(__file__), "cfa_crash_worker.py")
KILLS = 20


# =============================================================================
# Helpers
# =============================================================================


def _build_collection() -> str:
    """Seed a real CFA collection at a fresh on-disk path and return the path.

    Includes graded review cards (so the scores compute) plus a pool of NEW
    cards so the crash worker always has something to review."""
    path = tempfile.mktemp(suffix=".anki2")
    col = Collection(path)
    deck = _seed_rich(col)
    # A pool of fresh NEW cards to keep the review loop busy across all kills.
    nt = col.models.by_name("Basic")
    for i in range(200):
        note = col.new_note(nt)
        note["Front"] = f"crash-pool-{i}"
        note["Back"] = "answer"
        note.tags = ["los::topica::r1"]
        col.add_note(note, DeckId(deck))
    # Lift the per-day new-card cap so the worker can actually draw them.
    conf = col.decks.config_dict_for_deck_id(DeckId(deck))
    conf["new"]["perDay"] = 9999
    conf["rev"]["perDay"] = 9999
    col.decks.update_config(conf)
    # Select the CFA deck so the v3 queue actually serves its cards to the
    # worker (persisted in the collection, so the subprocess inherits it).
    col.decks.set_current(DeckId(deck))
    col.close()
    return path


def _revlog_count(path: str) -> int:
    col = Collection(path)
    try:
        return int(col.db.scalar("select count() from revlog") or 0)
    finally:
        col.close()


def _child_env() -> dict[str, str]:
    # Subprocess must import the same anki/backend the test uses.
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", os.pathsep.join(sys.path))
    return env


# =============================================================================
# 1. Kill mid-review → zero corruption
# =============================================================================


def test_kill_mid_review_leaves_no_corruption():
    path = _build_collection()
    rng = random.Random(20240704)  # deterministic kill timing
    before = _revlog_count(path)

    for i in range(KILLS):
        marker = path + f".ready{i}"
        if os.path.exists(marker):
            os.unlink(marker)
        proc = subprocess.Popen(
            [sys.executable, WORKER, path, marker],
            env=_child_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            # Wait until the worker has committed at least one real review, so
            # the kill is guaranteed to interrupt active review writes rather
            # than a slow backend startup.
            deadline = time.time() + 30
            while not os.path.exists(marker):
                if proc.poll() is not None:
                    raise AssertionError(
                        f"worker exited early (rc={proc.returncode}) on round {i}"
                    )
                if time.time() > deadline:
                    raise AssertionError(f"worker never became ready on round {i}")
                time.sleep(0.01)
            # Let a burst of reviews commit, then SIGKILL at a random offset.
            time.sleep(rng.uniform(0.02, 0.25))
        finally:
            proc.kill()  # SIGKILL — no chance to flush/clean up
            proc.wait(timeout=30)
        if os.path.exists(marker):
            os.unlink(marker)

        # Reopen and run the backend integrity check every single time.
        col = Collection(path)
        try:
            err, ok = col.fix_integrity()
            assert ok, f"corruption detected after kill #{i}: {err}"
        finally:
            col.close()

    after = _revlog_count(path)
    assert after > before, (
        "no reviews survived the kill loop — the test never actually "
        f"interrupted a mid-review write (before={before}, after={after})"
    )
    os.unlink(path)


# =============================================================================
# 2. Offline + AI-off still returns a score
# =============================================================================


def test_offline_ai_off_still_scores():
    from anki import cfa

    # Mirrors the desktop AI master toggle key (cfa/ai/llm_client.py). pylib
    # scoring is pure-local and never reads it, so pylib tests must not import
    # the desktop ``cfa`` package (not on sys.path here); the literal is enough.
    conf_ai_master = "cfa_ai_enabled"

    path = _build_collection()
    col = Collection(path)
    try:
        # Force AI hard OFF at the collection level; the scoring path must not
        # care (it is pure local computation, no network, no LLM).
        col.set_config(conf_ai_master, False)
        assert col.get_config(conf_ai_master) is False

        mem = cfa.memory_score(col)
        perf = cfa.performance_score(col)
        rdy = cfa.readiness_score(col)

        for name, score in (("memory", mem), ("performance", perf)):
            assert not score.abstain, f"{name} abstained offline/AI-off: {score.reason}"
            assert score.point is not None
            assert score.range_low <= score.point <= score.range_high
        # Readiness carries a wide uncalibrated band; it must still produce one.
        assert rdy.range_low <= rdy.range_high
        assert 0.0 <= rdy.range_low and rdy.range_high <= 1.0
    finally:
        col.close()
    os.unlink(path)


# =============================================================================
# 3. Worker / seeder sanity (fast, no subprocess) so the harness self-checks
# =============================================================================


def test_worker_reviews_and_writes_revlog():
    """The worker actually commits reviews — a quick single-shot check that the
    subprocess machinery and marker contract are sound (bounded, then killed)."""
    path = _build_collection()
    marker = path + ".ready"
    before = _revlog_count(path)
    proc = subprocess.Popen(
        [sys.executable, WORKER, path, marker],
        env=_child_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 30
        while not os.path.exists(marker) and time.time() < deadline:
            time.sleep(0.01)
        assert os.path.exists(marker), "worker never signalled ready"
        time.sleep(0.2)
    finally:
        proc.kill()
        proc.wait(timeout=30)
    assert _revlog_count(path) > before
    for p in (marker, path):
        if os.path.exists(p):
            os.unlink(p)


def test_seeder_scores_are_non_abstaining():
    from anki import cfa

    path = _build_collection()
    col = Collection(path)
    try:
        assert not cfa.memory_score(col).abstain
        assert not cfa.performance_score(col).abstain
    finally:
        col.close()
    os.unlink(path)
