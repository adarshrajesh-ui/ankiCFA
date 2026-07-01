from speedrun_scoring import CoverageMap
from speedrun_scoring.data import ReviewRecord


def _reviews_for(topics, per_topic):
    out = []
    cid = 0
    for t in topics:
        for i in range(per_topic):
            out.append(
                ReviewRecord(cid, t, float(i), 3, 5.0, was_new=(i == 0))
            )
            cid += 1
    return out


def test_outline_loads():
    cov = CoverageMap.load_outline()
    assert "topic_0" in cov.weights
    assert cov.weights["topic_2"] == 1.5


def test_full_coverage():
    cov = CoverageMap.load_outline()
    topics = list(cov.weights)
    reviews = _reviews_for(topics, per_topic=10)
    pct = cov.compute(reviews, min_reviews_per_topic=5)
    assert pct == 100.0
    assert cov.uncovered_topics() == []


def test_partial_coverage_is_weighted():
    cov = CoverageMap.load_outline()
    topics = list(cov.weights)
    # Only cover the first half of topics.
    covered = topics[: len(topics) // 2]
    reviews = _reviews_for(covered, per_topic=10)
    pct = cov.compute(reviews, min_reviews_per_topic=5)
    assert 0.0 < pct < 100.0
    assert set(cov.uncovered_topics()) == set(topics) - set(covered)


def test_new_only_reviews_do_not_count():
    cov = CoverageMap.load_outline()
    topics = list(cov.weights)
    reviews = [ReviewRecord(i, t, 0.0, 3, 5.0, was_new=True) for i, t in enumerate(topics)]
    pct = cov.compute(reviews, min_reviews_per_topic=1)
    assert pct == 0.0
