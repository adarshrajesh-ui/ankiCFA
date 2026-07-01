from speedrun_scoring import check_leakage
from speedrun_scoring.data import QuestionResult
from speedrun_scoring.leakage import jaccard


def _q(stem):
    return QuestionResult(topic="t", difficulty=0.5, correct=True, latency=10.0, stem=stem)


def test_jaccard_identical():
    assert jaccard("the quick brown fox", "the quick brown fox") == 1.0


def test_jaccard_disjoint():
    assert jaccard("alpha beta", "gamma delta") == 0.0


def test_detects_exact_duplicate():
    train = [_q("photosynthesis converts light energy into glucose")]
    test = [_q("photosynthesis converts light energy into glucose")]
    report = check_leakage(train, test)
    assert report.has_leakage
    assert report.leaked_test_count == 1


def test_detects_near_duplicate():
    train = [_q("the mitochondria is the powerhouse of the cell")]
    test = [_q("the mitochondria is the powerhouse of the cell today")]
    report = check_leakage(train, test, threshold=0.8)
    assert report.has_leakage


def test_clean_split_has_no_leakage():
    train = [_q("cell membrane structure and function")]
    test = [_q("enzyme kinetics and reaction rates")]
    report = check_leakage(train, test)
    assert not report.has_leakage
    assert report.leaked_test_count == 0
