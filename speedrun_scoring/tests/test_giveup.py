import pytest

from speedrun_scoring import ExamConfig, GiveUpRule, Score
from speedrun_scoring.tests.conftest import STAMP


@pytest.fixture
def cfg():
    return ExamConfig("t", "pass_fail", 0.0, 1.0, 0.5)


def test_default_thresholds():
    assert ExamConfig("t", "pass_fail", 0.0, 1.0, 0.5).min_graded_reviews == 200
    assert ExamConfig("t", "pass_fail", 0.0, 1.0, 0.5).min_coverage_pct == 50.0


def test_abstain_on_low_reviews(cfg):
    d = GiveUpRule(cfg).evaluate(graded_reviews=199, coverage_pct=90.0)
    assert d.abstain
    assert any("graded reviews" in r for r in d.reasons)


def test_abstain_on_low_coverage(cfg):
    d = GiveUpRule(cfg).evaluate(graded_reviews=500, coverage_pct=49.9)
    assert d.abstain
    assert any("coverage" in r for r in d.reasons)


def test_no_abstain_when_sufficient(cfg):
    d = GiveUpRule(cfg).evaluate(graded_reviews=200, coverage_pct=50.0)
    assert not d.abstain
    assert d.reasons == []


def test_thresholds_are_configurable():
    strict = ExamConfig(
        "t", "pass_fail", 0.0, 1.0, 0.5, min_graded_reviews=1000, min_coverage_pct=80.0
    )
    d = GiveUpRule(strict).evaluate(graded_reviews=500, coverage_pct=70.0)
    assert d.abstain
    assert len(d.reasons) == 2


def test_abstaining_score_cannot_carry_a_number():
    with pytest.raises(ValueError):
        Score(
            point=0.5,
            range=(0.4, 0.6),
            coverage_pct=10.0,
            confidence=0.0,
            updated_at=STAMP,
            abstain=True,
        )


def test_nonabstaining_score_requires_point():
    with pytest.raises(ValueError):
        Score(
            point=None,
            range=None,
            coverage_pct=90.0,
            confidence=0.5,
            updated_at=STAMP,
            abstain=False,
        )


def test_score_point_must_lie_in_range():
    with pytest.raises(ValueError):
        Score(
            point=0.9,
            range=(0.1, 0.5),
            coverage_pct=90.0,
            confidence=0.5,
            updated_at=STAMP,
        )
