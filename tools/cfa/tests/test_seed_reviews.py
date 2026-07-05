# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the populated-render review seeder (Phase B desktop Pass 2).

``seed_reviews.seed_review_history`` must turn a freshly seeded CFA collection
(which honestly ABSTAINS on a zero-review first run) into one whose memory /
performance / readiness scores render REAL ranges — i.e. it must cross every
give-up threshold in ``anki.cfa`` (>=200 graded reviews, >=50% coverage,
>=30 first exposures, no high-weight topic skipped). These tests assert that
against the real shared engine, plus determinism and the honest guard-rails.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

import pytest

REPO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
for _p in (
    os.path.join(REPO, "out", "pylib"),
    os.path.join(REPO, "pylib"),
    os.path.join(REPO, "tools", "cfa"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from anki.collection import Collection

    _HAVE_BACKEND = True
except Exception:
    _HAVE_BACKEND = False

needs_backend = pytest.mark.skipif(
    not _HAVE_BACKEND, reason="built pylib backend not on path"
)


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(REPO, "tools", "cfa", filename)
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


SR = _load("cfa_seed_reviews", "seed_reviews.py")


@pytest.fixture
def seeded_col():
    """A fresh CFA collection with the decks loaded but zero reviews."""
    import seed_collection

    with tempfile.TemporaryDirectory(prefix="cfa-seedrev-") as d:
        col = Collection(os.path.join(d, "collection.anki2"))
        seed_collection.seed_collection(col, repo_root=REPO)
        try:
            yield col
        finally:
            col.close()


# --- pure shape --------------------------------------------------------------


def test_constants_clear_thresholds():
    from anki import cfa

    # 10 topics * PER_TOPIC * REVIEWS_EACH must clear MIN_GRADED_REVIEWS, and
    # one first exposure per seeded card must clear MIN_FIRST_EXPOSURES.
    topics = len(cfa.CANONICAL_TOPICS)
    assert topics * SR.PER_TOPIC * SR.REVIEWS_EACH >= cfa.MIN_GRADED_REVIEWS
    assert topics * SR.PER_TOPIC >= cfa.MIN_FIRST_EXPOSURES


# --- against the real engine -------------------------------------------------


@needs_backend
def test_fresh_deck_abstains_before_seeding(seeded_col):
    """The honesty baseline: a zero-review CFA deck abstains on all 3 scores."""
    from anki import cfa

    did = seeded_col.decks.id_for_name("CFA Level II")
    assert cfa.memory_score(seeded_col, deck_id=did).abstain
    assert cfa.performance_score(seeded_col, deck_id=did).abstain
    assert cfa.readiness_score(seeded_col, deck_id=did).abstain


@needs_backend
def test_seeding_crosses_all_thresholds(seeded_col):
    from anki import cfa

    res = SR.seed_review_history(seeded_col)
    did = seeded_col.decks.id_for_name("CFA Level II")

    mem = cfa.memory_score(seeded_col, deck_id=did)
    perf = cfa.performance_score(seeded_col, deck_id=did)
    rdy = cfa.readiness_score(seeded_col, deck_id=did)

    # No longer abstaining — real ranges rendered.
    assert not mem.abstain and not perf.abstain and not rdy.abstain
    assert mem.point is not None and mem.range_low is not None
    assert perf.point is not None
    assert rdy.point is not None

    # Thresholds genuinely cleared.
    assert res["graded_reviews"] >= cfa.MIN_GRADED_REVIEWS
    assert res["first_exposures"] >= cfa.MIN_FIRST_EXPOSURES
    assert res["coverage_pct"] >= cfa.MIN_TOPIC_COVERAGE
    # Every topic covered => no high-weight topic skipped.
    assert res["coverage_pct"] == pytest.approx(1.0)


@needs_backend
def test_accuracy_is_realistic_not_perfect(seeded_col):
    """~30% of exposures fail, so performance must not be a fake 100%."""
    from anki import cfa

    SR.seed_review_history(seeded_col)
    did = seeded_col.decks.id_for_name("CFA Level II")
    perf = cfa.performance_score(seeded_col, deck_id=did)
    assert 0.4 < perf.point < 0.95


@needs_backend
def test_recall_spread_is_realistic_not_flat(seeded_col):
    """Per-topic recall must vary (not a degenerate flat 100%) so the coverage
    map reads as real study data, not a fake seed."""
    from anki import cfa

    SR.seed_review_history(seeded_col)
    did = seeded_col.decks.id_for_name("CFA Level II")
    mem = cfa.memory_score(seeded_col, deck_id=did)
    recalls = [t.avg_r for t in mem.topics if t.avg_r is not None]
    assert len(recalls) == 10
    # No topic is a perfect 100%, and there is a genuine spread across topics.
    assert max(recalls) < 0.999
    assert max(recalls) - min(recalls) > 0.02


@needs_backend
def test_deterministic(seeded_col):
    """Two seedings of equivalent fresh collections yield identical readiness."""
    import seed_collection

    res_a = SR.seed_review_history(seeded_col)

    with tempfile.TemporaryDirectory(prefix="cfa-seedrev-b-") as d:
        col_b = Collection(os.path.join(d, "collection.anki2"))
        seed_collection.seed_collection(col_b, repo_root=REPO)
        res_b = SR.seed_review_history(col_b)
        col_b.close()

    assert res_a["graded_reviews"] == res_b["graded_reviews"]
    assert res_a["readiness_point"] == pytest.approx(res_b["readiness_point"])
    assert res_a["memory_point"] == pytest.approx(res_b["memory_point"])


@needs_backend
def test_raises_when_no_cfa_cards():
    """Seeding an empty collection (no CFA deck) fails loudly, never silently."""
    with tempfile.TemporaryDirectory(prefix="cfa-empty-") as d:
        col = Collection(os.path.join(d, "collection.anki2"))
        try:
            with pytest.raises(RuntimeError):
                SR.seed_review_history(col)
        finally:
            col.close()
