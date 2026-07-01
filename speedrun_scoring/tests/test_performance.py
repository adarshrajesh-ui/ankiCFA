from speedrun_scoring import MemoryModel, PASS_FAIL_EXAMPLE, PerformanceModel
from speedrun_scoring.performance import paraphrase_gap
from speedrun_scoring.tests.conftest import STAMP


def test_performance_differs_from_memory(fixture, at_ts):
    mem = MemoryModel(PASS_FAIL_EXAMPLE).score(fixture.reviews, 75.0, at_ts, STAMP)
    perf = PerformanceModel(PASS_FAIL_EXAMPLE).score(
        fixture.reviews, fixture.questions, 75.0, at_ts, STAMP
    )
    # The whole point of the layer: recall != question performance.
    assert abs(mem.point - perf.point) > 0.05


def test_paraphrase_gap_positive(fixture, at_ts):
    mem = MemoryModel(PASS_FAIL_EXAMPLE)
    cards = mem.fit(fixture.reviews)
    tm = mem.topic_mastery(cards, at_ts)
    gap = paraphrase_gap(tm, fixture.questions)
    assert gap > 0.0


def test_predict_question_respects_transfer():
    m = PerformanceModel(PASS_FAIL_EXAMPLE)
    mastery = 0.9
    easy = m.predict_question(mastery, difficulty=0.0)
    hard = m.predict_question(mastery, difficulty=1.0)
    assert easy > hard
    # transfer < 1 means performance below raw mastery.
    assert easy < mastery


def test_range_brackets_point(fixture, at_ts):
    s = PerformanceModel(PASS_FAIL_EXAMPLE).score(
        fixture.reviews, fixture.questions, 75.0, at_ts, STAMP
    )
    assert s.range[0] <= s.point <= s.range[1]
    assert 0.0 <= s.range[0] and s.range[1] <= 1.0


def test_performance_abstains_when_thin(at_ts):
    s = PerformanceModel(PASS_FAIL_EXAMPLE).score([], [], 0.0, at_ts, STAMP)
    assert s.abstain
    assert s.point is None
