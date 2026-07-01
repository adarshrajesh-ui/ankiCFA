from speedrun_scoring import ExamConfig, MemoryModel, PASS_FAIL_EXAMPLE
from speedrun_scoring.data import ReviewRecord
from speedrun_scoring.tests.conftest import STAMP


def test_recall_in_unit_interval(fixture, at_ts):
    model = MemoryModel(PASS_FAIL_EXAMPLE)
    cards = model.fit(fixture.reviews)
    for cm in cards.values():
        r = cm.recall(at_ts)
        assert 0.0 <= r <= 1.0


def test_recall_decays_with_time(fixture):
    model = MemoryModel(PASS_FAIL_EXAMPLE)
    cards = model.fit(fixture.reviews)
    cm = next(iter(cards.values()))
    early = cm.recall(cm.last_ts + 1.0)
    late = cm.recall(cm.last_ts + 100.0)
    assert early > late


def test_interval_brackets_point(fixture, at_ts):
    model = MemoryModel(PASS_FAIL_EXAMPLE)
    cards = model.fit(fixture.reviews)
    for cm in cards.values():
        lo, hi = cm.recall_interval(at_ts)
        assert lo <= cm.recall(at_ts) <= hi
        assert 0.0 <= lo <= hi <= 1.0


def test_score_object_fields(fixture, at_ts):
    s = MemoryModel(PASS_FAIL_EXAMPLE).score(fixture.reviews, 75.0, at_ts, STAMP)
    assert not s.abstain
    assert s.point is not None and s.range is not None
    assert s.range[0] <= s.point <= s.range[1]
    assert 0.0 <= s.confidence <= 1.0
    assert s.updated_at == STAMP


def test_score_abstains_when_thin():
    cfg = PASS_FAIL_EXAMPLE
    thin = [
        ReviewRecord(0, "topic_0", float(i), 3, 5.0, was_new=(i == 0))
        for i in range(3)
    ]
    s = MemoryModel(cfg).score(thin, 10.0, 10.0, STAMP)
    assert s.abstain
    assert s.point is None and s.range is None
    assert s.reasons


def test_more_reviews_narrows_interval():
    cfg = ExamConfig("t", "pass_fail", 0.0, 1.0, 0.5)
    model = MemoryModel(cfg)
    few = [ReviewRecord(0, "t", float(i), 3, 5.0, was_new=(i == 0)) for i in range(2)]
    many = [ReviewRecord(0, "t", float(i), 3, 5.0, was_new=(i == 0)) for i in range(12)]
    cm_few = model.fit_card(few)
    cm_many = model.fit_card(many)
    lo_f, hi_f = cm_few.recall_interval(cm_few.last_ts)
    lo_m, hi_m = cm_many.recall_interval(cm_many.last_ts)
    assert (hi_m - lo_m) < (hi_f - lo_f)
