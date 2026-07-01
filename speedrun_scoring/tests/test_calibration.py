from speedrun_scoring import PASS_FAIL_EXAMPLE
from speedrun_scoring.calibration import (
    brier_score,
    calibrate,
    log_loss,
    reliability_curve,
)


def test_brier_and_logloss_perfect():
    assert brier_score([1.0, 0.0], [1, 0]) == 0.0
    assert log_loss([1.0, 0.0], [1, 0]) < 1e-6


def test_brier_worst_case():
    assert abs(brier_score([0.0, 1.0], [1, 0]) - 1.0) < 1e-9


def test_reliability_curve_counts():
    preds = [0.05, 0.15, 0.95]
    obs = [0, 0, 1]
    curve = reliability_curve(preds, obs, n_bins=10)
    total = sum(c for *_rest, c in curve)
    assert total == len(preds)


def test_calibration_on_fixture_is_reasonable(fixture):
    report = calibrate(PASS_FAIL_EXAMPLE, fixture.reviews)
    assert report.n > 0
    # Held-out predictions should track observed outcomes on synthetic data.
    assert report.brier < 0.25
    assert report.log_loss < 1.0
    # Reliability bins never over-count.
    assert sum(c for *_r, c in report.reliability) == report.n


def test_calibration_empty_is_nan():
    report = calibrate(PASS_FAIL_EXAMPLE, [])
    assert report.n == 0
    assert report.brier != report.brier  # nan
