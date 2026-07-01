# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Pure tests for the dashboard renderer + revlog->cluster mapping helper (no anki needed)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ethics_dashboard  # noqa: E402
import ethics_revlog  # noqa: E402
from ethics_scoring import AttemptRecord, discrimination_by_cluster  # noqa: E402


def test_render_shows_not_enough_data_when_abstaining():
    scores = discrimination_by_cluster(
        [AttemptRecord("mnpi", True, 1), AttemptRecord("mnpi", True, 2)]
    )
    html = ethics_dashboard.render_dashboard_html(scores, {"mnpi": "II(A) MNPI"})
    assert "Not enough data" in html
    assert "II(A) MNPI" in html


def test_render_shows_percentage_and_ci_when_scored():
    recs = [AttemptRecord("mnpi", i % 2 == 0, i) for i in range(10)]  # 5/10 correct
    scores = discrimination_by_cluster(recs)
    html = ethics_dashboard.render_dashboard_html(scores, {"mnpi": "II(A) MNPI"})
    assert "50<span" in html or "50%" in html  # point estimate rendered
    assert "95% CI" in html


def test_render_carries_honest_disclaimer_not_a_score_claim():
    html = ethics_dashboard.render_dashboard_html({}, {})
    assert "Evidence-grounded mechanism" in html
    assert "not a claim" in html.lower()
    # never overclaim
    assert "proven to raise" not in html.lower().replace(
        "not a claim that the feature is proven to raise", ""
    )


def test_cluster_from_tags_extracts_cluster():
    assert (
        ethics_revlog.cluster_from_tags(
            " los::ethics::ii-a-mnpi cluster::suitability-mnpi-diligence "
        )
        == "suitability-mnpi-diligence"
    )
    assert ethics_revlog.cluster_from_tags(" los::ethics::x ") is None
    assert ethics_revlog.cluster_from_tags("") is None
