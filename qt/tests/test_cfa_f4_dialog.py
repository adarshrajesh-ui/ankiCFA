# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F4 — the Exam Readiness payload carries the Bayesian CI + pass/fail call.

The Exam Readiness surface is now the shared SvelteKit page (``ts/lib/cfa``)
embedded in ``aqt.cfa.ExamReadinessDialog`` via an ``AnkiWebView``. The honest
scores it renders come from ``aqt.mediasrv._cfa_exam_readiness_payload`` — the
SAME ``anki.cfa`` data the old Qt body rendered. These tests build that payload
against a live collection with seeded reviews and assert the F4 hero carries the
call, the 95% credible band and the "not validated" caveat — and that it
ABSTAINS (no confident call, no CI) below the give-up threshold.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from anki import cfa as anki_cfa
from anki.collection import Collection
from aqt.mediasrv import _cfa_exam_readiness_payload

DAY = 86_400
_APP: QApplication | None = None


def _app() -> QApplication:
    # Importing aqt pulls in Qt; keep a QApplication alive for parity with the
    # other offscreen CFA tests even though the payload builder itself is pure.
    global _APP
    _APP = QApplication.instance() or QApplication(["test"])  # type: ignore[assignment]
    return _APP  # type: ignore[return-value]


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def _seed(
    col: Collection,
    topic: str,
    n_cards: int,
    reviews_each: int,
    frac_ok: float,
    *,
    deck_name: str = "CFA",
    configure: bool = True,
):
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id(deck_name)
    cids = []
    for i in range(n_cards):
        note = col.new_note(nt)
        note["Front"] = f"{topic}-{i}"
        note["Back"] = "a"
        note.tags = [f"{topic}::r1"]
        col.add_note(note, deck)
        cids.append(col.find_cards(f"nid:{note.id}")[0])
    col.sched.set_due_date(cids, "0")
    data = json.dumps({"s": 100.0, "d": 5.0, "lrt": now - DAY})
    col.db.executemany(
        "update cards set data=?, ivl=? where id=?", [(data, 20, c) for c in cids]
    )
    n_ok = round(n_cards * frac_ok)
    first_ease = [3] * n_ok + [1] * (n_cards - n_ok)
    # Spread each card's reviews across DISTINCT collection-days: the scoring
    # engine dedups graded reviews per-(card, day) (so a card reviewed twice in
    # one day — e.g. offline on two devices — is not double-counted). Fake
    # same-day revlog ids would collapse every review of a card into one day, so
    # "reviews_each" study sessions must land on separate days to count. j == 0
    # is the OLDEST review (a card's first exposure); the per-card +idx offset
    # keeps revlog ids globally unique without crossing a day boundary.
    now_ms = int(time.time() * 1000)
    anchor_ms = now_ms - reviews_each * DAY * 1000
    rows = []
    for idx, c in enumerate(cids):
        for j in range(reviews_each):
            ease = first_ease[idx] if j == 0 else 3
            rid = anchor_ms + j * DAY * 1000 + idx
            rows.append((rid, c, -1, ease, 10, 5, 2500, 1000, 1))
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    if configure:
        anki_cfa.set_exam_config(
            col, exam_date="2026-12-01", topic_weights={topic: 1.0}
        )
    return deck


def test_payload_renders_call_and_ci_for_strong_deck() -> None:
    _app()
    col = _empty_col()
    deck = _seed(col, "los::topica", n_cards=40, reviews_each=8, frac_ok=0.95)
    try:
        payload = _cfa_exam_readiness_payload(col, int(deck))
        assert payload["heroMode"] == "bayesian_call"
        hero = payload["heroBayesian"]
        assert hero["call"] == "likely pass"
        assert hero["passed"] is True
        # The 95% credible band is present as a low/high pair.
        assert hero["ciLow"] is not None and hero["ciHigh"] is not None
        assert hero["ciLow"] <= hero["ciHigh"]
        # The standing "not validated" caveat rides along on the call + band.
        assert hero["label"] == "not validated against real exam data"
        assert payload["readiness"]["label"] == "not validated against real exam data"
    finally:
        col.close()


def test_payload_hero_abstains_below_giveup_threshold() -> None:
    # item3 sub-bug 3A — with only two graded reviews the give-up rule fires
    # (memory_score.abstain), so the hero must ABSTAIN — no confident call, no
    # "p=" probability and no accuracy CI — matching the honest bands beneath it.
    _app()
    col = _empty_col()
    deck = _seed(col, "los::topica", n_cards=2, reviews_each=1, frac_ok=1.0)
    try:
        # Precondition: the give-up rule actually fires for this deck.
        assert anki_cfa.memory_score(col, deck_id=deck).abstain

        payload = _cfa_exam_readiness_payload(col, int(deck))
        assert payload["heroMode"] == "abstain"
        # No confident Bayesian call block at all.
        assert "heroBayesian" not in payload
        abstain = payload["heroAbstain"]
        assert abstain["reason"]
        # The honesty caveat is still surfaced.
        assert abstain["readinessLabel"] == "not validated against real exam data"
    finally:
        col.close()


def test_payload_hero_shows_call_above_giveup_threshold() -> None:
    # item3 sub-bug 3A — the complement: with enough graded reviews and coverage
    # the give-up rule does NOT fire, so the confident Bayesian call is shown
    # exactly as before (a call, its probability, and the 95% CI band).
    _app()
    col = _empty_col()
    deck = _seed(col, "los::topica", n_cards=40, reviews_each=6, frac_ok=0.95)
    try:
        assert not anki_cfa.memory_score(col, deck_id=deck).abstain

        payload = _cfa_exam_readiness_payload(col, int(deck))
        assert payload["heroMode"] == "bayesian_call"
        hero = payload["heroBayesian"]
        assert hero["call"] in ("likely pass", "likely fail")
        assert 0.0 <= hero["callProb"] <= 1.0
        assert hero["ciLow"] is not None and hero["ciHigh"] is not None
    finally:
        col.close()


def test_payload_hero_abstains_when_only_performance_gives_up() -> None:
    # review-1 — the hero must abstain whenever ANY give-up-gated band does, not
    # just Memory. Here >=200 graded reviews spread over <30 distinct cards means
    # memory_score does NOT abstain (enough reviews, full coverage) but
    # performance_score DOES (first_exposures < MIN_FIRST_EXPOSURES=30). The hero
    # must still abstain — no confident call, no CI.
    _app()
    col = _empty_col()
    deck = _seed(col, "los::topica", n_cards=20, reviews_each=12, frac_ok=0.95)
    try:
        assert not anki_cfa.memory_score(col, deck_id=deck).abstain
        perf = anki_cfa.performance_score(col, deck_id=deck)
        assert perf.abstain and perf.first_exposures < anki_cfa.MIN_FIRST_EXPOSURES

        payload = _cfa_exam_readiness_payload(col, int(deck))
        assert payload["heroMode"] == "abstain"
        assert "heroBayesian" not in payload
        assert payload["heroAbstain"]["reason"]
    finally:
        col.close()


def test_payload_topic_count_is_canonical_and_consistent() -> None:
    # item3 sub-bug 3B — topic rows == caption total == canonical 8. With no exam
    # config the readiness scores fall back to the canonical topic list, so the
    # per-topic rows, the "N/total topics" caption and score.topics all resolve
    # to the same eight authored CFA topics (and the payload builds without the
    # old no-config crash).
    _app()
    col = _empty_col()
    deck = _seed(
        col, "los::ethics", n_cards=5, reviews_each=3, frac_ok=0.8, configure=False
    )
    try:
        assert anki_cfa.get_exam_config(col) is None
        score = anki_cfa.memory_score(col, deck_id=deck)
        assert score.topics_total == 8
        assert len(score.topics) == 8

        payload = _cfa_exam_readiness_payload(col, int(deck))
        assert len(payload["topics"]) == 8, "one row per canonical topic"
        assert payload["caption"]["topicsTotal"] == 8
    finally:
        col.close()


def test_payload_topic_rows_show_human_names_not_raw_slugs() -> None:
    # Polish fix — the per-topic table must present readable CFA topic-area
    # NAMES (e.g. "Financial Reporting & Analysis"), never the raw
    # ``los::<slug>`` join-key tags that leaked through before. The payload maps
    # each topic slug to its canonical display name (behaviour otherwise
    # identical: same rows, order and numbers).
    _app()
    col = _empty_col()
    deck = _seed(
        col, "los::ethics", n_cards=5, reviews_each=3, frac_ok=0.8, configure=False
    )
    try:
        payload = _cfa_exam_readiness_payload(col, int(deck))
        names = [t["topic"] for t in payload["topics"]]
        # No raw ``los::`` slug leaks into the displayed topic column.
        assert not any(n.startswith("los::") for n in names), names
        # The canonical CFA topic-area names are what the table shows.
        assert "Ethics & Professional Standards" in names
        assert "Financial Reporting & Analysis" in names
        assert "Portfolio Management" in names
        assert "Alternative Investments" in names
    finally:
        col.close()
