from speedrun_scoring import PASS_FAIL_EXAMPLE, SCALED_EXAMPLE, ReadinessModel
from speedrun_scoring.tests.conftest import STAMP


def test_pass_fail_probability_in_unit(fixture, at_ts):
    s = ReadinessModel(PASS_FAIL_EXAMPLE).score(
        fixture.reviews, fixture.questions, 75.0, at_ts, STAMP
    )
    assert not s.abstain
    assert 0.0 <= s.point <= 1.0
    assert 0.0 <= s.range[0] <= s.range[1] <= 1.0
    assert 0.0 <= s.confidence <= 1.0


def test_scaled_score_within_config_scale(fixture, at_ts):
    cfg = SCALED_EXAMPLE
    s = ReadinessModel(cfg).score(
        fixture.reviews, fixture.questions, 75.0, at_ts, STAMP
    )
    assert cfg.scale_min <= s.range[0] <= s.point <= s.range[1] <= cfg.scale_max


def test_readiness_abstains(at_ts):
    s = ReadinessModel(PASS_FAIL_EXAMPLE).score([], [], 0.0, at_ts, STAMP)
    assert s.abstain
    assert s.point is None and s.range is None
    assert s.confidence == 0.0


def test_scale_is_config_driven(fixture, at_ts):
    # Same data, different configured scale -> different reported scale.
    pf = ReadinessModel(PASS_FAIL_EXAMPLE).score(
        fixture.reviews, fixture.questions, 75.0, at_ts, STAMP
    )
    sc = ReadinessModel(SCALED_EXAMPLE).score(
        fixture.reviews, fixture.questions, 75.0, at_ts, STAMP
    )
    assert pf.point <= 1.0
    assert sc.point > 100.0
