from speedrun_scoring import generate_fixture
from speedrun_scoring.data import graded_review_count, retrievability


def test_fixture_is_deterministic():
    a = generate_fixture(seed=42)
    b = generate_fixture(seed=42)
    assert a.reviews == b.reviews
    assert a.questions == b.questions


def test_different_seeds_differ():
    a = generate_fixture(seed=1)
    b = generate_fixture(seed=2)
    assert a.reviews != b.reviews


def test_record_shapes(fixture):
    r = fixture.reviews[0]
    assert isinstance(r.card_id, int)
    assert 1 <= r.grade <= 4
    assert r.latency > 0
    q = fixture.questions[0]
    assert 0.0 <= q.difficulty <= 1.0
    assert isinstance(q.correct, bool)
    assert q.stem


def test_graded_excludes_new(fixture):
    graded = graded_review_count(fixture.reviews)
    total = len(fixture.reviews)
    new = sum(1 for r in fixture.reviews if r.was_new)
    assert graded == total - new
    assert graded > 0


def test_retrievability_monotonic_decreasing():
    s = 5.0
    assert retrievability(0.0, s) == 1.0
    assert retrievability(1.0, s) > retrievability(10.0, s)
    assert 0.0 < retrievability(100.0, s) < 1.0


def test_retrievability_hits_target_at_stability():
    # By construction R == 0.9 when elapsed == stability.
    assert abs(retrievability(5.0, 5.0) - 0.9) < 1e-9
