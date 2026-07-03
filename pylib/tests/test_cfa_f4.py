# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Feature F4: honest Bayesian readiness — a number from the first review.

F4 replaces the Feature-6 "not enough data" give-up wall with an honest
uncertainty band:

* SM-2 fallback — :func:`cfa.estimate_recall` yields a recall number from the
  first review even when FSRS retrievability R is NULL.
* Bayesian CI — :func:`cfa.bayesian_readiness` reports a 95% credible band on
  exam-weighted accuracy that starts WIDE (uniform priors) and NARROWS as
  reviews accrue, and NEVER abstains.
* Explicit call — a "likely pass"/"likely fail" verdict with a probability
  computed against the ~65% MPS proxy, keeping the "not validated" caveat.

Pure-function tests pin the maths; collection-backed tests pin the end-to-end
shape and the widen/narrow behaviour.
"""

from __future__ import annotations

import time

from anki import cfa
from anki.collection import Collection
from anki.decks import DeckId
from tests.shared import getEmptyCol

# Reuse the Feature-6 seeding helpers verbatim.
from tests.test_cfa_scores import _seed_topic

DAY = 86_400


# =============================================================================
# SM-2 fallback recall (pure)
# =============================================================================


def test_estimate_recall_uses_fsrs_r_when_present():
    # FSRS R is authoritative and passed through untouched.
    assert cfa.estimate_recall(0.83, 20, 5, 3, 4) == 0.83
    # Clamped into [0, 1].
    assert cfa.estimate_recall(1.5, 20, 5, 3, 4) == 1.0


def test_estimate_recall_sm2_fallback_yields_a_number_when_r_is_null():
    # The core F4 fix: R is NULL but there is review history -> still a number.
    rec = cfa.estimate_recall(None, ivl_days=20, elapsed_days=0, successes=1, total=1)
    assert rec is not None
    assert 0.0 <= rec <= 1.0
    # Fresh review (elapsed 0) on a perfect card -> high recall.
    assert rec > 0.9


def test_estimate_recall_decays_with_elapsed_time():
    fresh = cfa.estimate_recall(None, 20, 0, 5, 5)
    stale = cfa.estimate_recall(None, 20, 200, 5, 5)
    assert fresh is not None and stale is not None
    assert stale < fresh, "recall must decay as time passes the interval"


def test_estimate_recall_penalises_lapses():
    perfect = cfa.estimate_recall(None, 20, 5, 4, 4)
    lapsy = cfa.estimate_recall(None, 20, 5, 1, 4)
    assert perfect is not None and lapsy is not None
    assert lapsy < perfect, "empirical failures drag recall down"


def test_estimate_recall_none_without_any_history():
    assert cfa.estimate_recall(None, None, None, 0, 0) is None


# =============================================================================
# Beta posterior maths (pure)
# =============================================================================


def test_beta_posterior_and_mean_var():
    a, b = cfa._beta_posterior(3, 1)  # uniform prior + 3 wins, 1 loss
    assert (a, b) == (4.0, 2.0)
    mean, var = cfa._beta_mean_var(a, b)
    assert abs(mean - 4.0 / 6.0) < 1e-12
    assert var > 0


def test_beta_variance_shrinks_with_more_data():
    _m1, v_small = cfa._beta_mean_var(*cfa._beta_posterior(3, 3))
    _m2, v_big = cfa._beta_mean_var(*cfa._beta_posterior(300, 300))
    assert v_big < v_small, "more evidence -> tighter posterior"


def test_no_evidence_is_uniform_prior():
    a, b = cfa._beta_posterior(0, 0)
    mean, var = cfa._beta_mean_var(a, b)
    assert mean == 0.5
    assert abs(var - 1.0 / 12.0) < 1e-12  # Var of Uniform(0,1)


# =============================================================================
# Bayesian readiness — end to end (never abstains; band widens/narrows)
# =============================================================================


def _seed_correct(
    col: Collection,
    deck: DeckId,
    topic: str,
    *,
    n_cards: int,
    reviews_each: int,
    frac_correct: float,
    stability: float = 100.0,
) -> None:
    now = int(time.time())
    nt = col.models.by_name("Basic")
    n_correct = round(n_cards * frac_correct)
    first_ease = [3] * n_correct + [1] * (n_cards - n_correct)
    _seed_topic(
        col,
        deck,
        nt,
        topic,
        n_cards,
        stability=stability,
        reviews_each=reviews_each,
        first_ease=first_ease,
        now=now,
    )


def test_readiness_never_abstains_and_is_wide_with_little_data():
    col = getEmptyCol()
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    # A single lightly-reviewed topic: barely any evidence.
    _seed_topic(
        col,
        deck,
        nt,
        "los::topica",
        2,
        stability=100.0,
        reviews_each=1,
        first_ease=[3, 3],
        now=int(time.time()),
    )
    cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights={"los::topica": 1.0})
    r = cfa.bayesian_readiness(col, deck_id=deck)
    # Never abstains: always a numeric band + a call.
    assert 0.0 <= r.ci_low <= r.accuracy <= r.ci_high <= 1.0
    assert r.call in ("likely pass", "likely fail")
    assert 0.5 <= r.call_prob <= 1.0
    assert r.label == "not validated against real exam data"
    # Little data -> wide band.
    assert (r.ci_high - r.ci_low) > 0.25
    col.close()


def test_readiness_band_narrows_as_reviews_accrue():
    col_small = getEmptyCol()
    deck_s = col_small.decks.id("CFA")
    _seed_correct(
        col_small, deck_s, "los::t", n_cards=4, reviews_each=1, frac_correct=0.75
    )
    cfa.set_exam_config(
        col_small, exam_date="2026-12-01", topic_weights={"los::t": 1.0}
    )
    small = cfa.bayesian_readiness(col_small, deck_id=deck_s)

    col_big = getEmptyCol()
    deck_b = col_big.decks.id("CFA")
    _seed_correct(
        col_big, deck_b, "los::t", n_cards=40, reviews_each=10, frac_correct=0.75
    )
    cfa.set_exam_config(col_big, exam_date="2026-12-01", topic_weights={"los::t": 1.0})
    big = cfa.bayesian_readiness(col_big, deck_id=deck_b)

    assert big.first_exposures > small.first_exposures
    assert (big.ci_high - big.ci_low) < (small.ci_high - small.ci_low), (
        "the 95% band must narrow as reviews accrue"
    )
    col_small.close()
    col_big.close()


def test_readiness_call_is_pass_for_strong_deck():
    col = getEmptyCol()
    deck = col.decks.id("CFA")
    # Lots of reviews, mostly correct -> should call a pass with high prob.
    _seed_correct(col, deck, "los::t", n_cards=40, reviews_each=10, frac_correct=0.95)
    cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights={"los::t": 1.0})
    r = cfa.bayesian_readiness(col, deck_id=deck)
    assert r.call == "likely pass"
    assert r.p_pass > 0.65
    assert r.accuracy > r.mps
    col.close()


def test_readiness_call_is_fail_for_weak_deck():
    col = getEmptyCol()
    deck = col.decks.id("CFA")
    _seed_correct(col, deck, "los::t", n_cards=40, reviews_each=10, frac_correct=0.30)
    cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights={"los::t": 1.0})
    r = cfa.bayesian_readiness(col, deck_id=deck)
    assert r.call == "likely fail"
    assert r.p_pass < 0.35
    assert r.accuracy < r.mps
    col.close()


def test_uncovered_high_weight_topic_widens_band_without_abstaining():
    col = getEmptyCol()
    deck = col.decks.id("CFA")
    # Studied one topic thoroughly, but a second high-weight topic is untouched.
    _seed_correct(
        col, deck, "los::studied", n_cards=40, reviews_each=10, frac_correct=0.9
    )
    cfa.set_exam_config(
        col,
        exam_date="2026-12-01",
        topic_weights={"los::studied": 0.5, "los::untouched": 0.5},
    )
    r = cfa.bayesian_readiness(col, deck_id=deck)
    assert r.topics_total == 2
    assert r.topics_covered == 1
    by = {t.topic: t for t in r.topics}
    # The untouched topic sits at the uniform prior (mean 0.5, wide band).
    assert abs(by["los::untouched"].mean - 0.5) < 1e-9
    assert by["los::untouched"].recall is None
    # Still no abstention — a call is always made.
    assert r.call in ("likely pass", "likely fail")
    col.close()


def test_readiness_reports_recall_with_sm2_fallback_when_r_null():
    col = getEmptyCol()
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    # stability makes FSRS R computable; to force the SM-2 path we blank c.data.
    cids = _seed_topic(
        col,
        deck,
        nt,
        "los::t",
        4,
        stability=100.0,
        reviews_each=3,
        first_ease=[3, 3, 3, 3],
        now=now,
    )
    col.db.executemany("update cards set data='' where id=?", [(c,) for c in cids])
    cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights={"los::t": 1.0})
    r = cfa.bayesian_readiness(col, deck_id=deck)
    # Even with FSRS R NULL, a recall number is produced from review history.
    assert r.recall is not None
    assert 0.0 <= r.recall <= 1.0
    col.close()
