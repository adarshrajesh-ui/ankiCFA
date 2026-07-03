# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F4 — ExamReadinessDialog shows the Bayesian CI + the explicit pass/fail call.

Builds the real ``aqt.cfa.ExamReadinessDialog`` against a live collection with
seeded reviews (offscreen Qt) and asserts the F4 hero block renders the call,
the 95% credible band, and the "not validated" caveat — and that the dialog
renders at all when there is essentially no data (no give-up wall).
"""

from __future__ import annotations

import json
import os
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from anki import cfa as anki_cfa
from anki.collection import Collection
from aqt import cfa

DAY = 86_400
_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication(["test"])  # type: ignore[assignment]
    return _APP  # type: ignore[return-value]


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


class _StandInMW(QWidget):
    def __init__(self, col: Collection) -> None:
        _app()
        super().__init__()
        self.col = col


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
    base = (col.db.scalar("select coalesce(max(id),0) from revlog") or 0) + 1
    rows, k = [], 0
    for idx, c in enumerate(cids):
        for j in range(reviews_each):
            ease = first_ease[idx] if j == 0 else 3
            rows.append((base + k, c, -1, ease, 10, 5, 2500, 1000, 1))
            k += 1
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


def test_dialog_renders_call_and_ci_for_strong_deck() -> None:
    col = _empty_col()
    deck = _seed(col, "los::topica", n_cards=40, reviews_each=8, frac_ok=0.95)
    mw = _StandInMW(col)
    dlg = cfa.ExamReadinessDialog(mw, deck)  # type: ignore[arg-type]
    from PyQt6.QtWidgets import QLabel

    text = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
    assert "likely pass" in text
    assert "95% CI" in text
    assert "not validated against real exam data" in text
    dlg.close()
    col.close()


def test_dialog_hero_abstains_below_giveup_threshold() -> None:
    # item3 sub-bug 3A (this test was previously
    # ``test_dialog_renders_with_almost_no_data_no_giveup_wall``, which asserted
    # the OPPOSITE). With only two graded reviews the give-up rule fires
    # (memory_score.abstain), so the hero must ABSTAIN — "keep studying", NO
    # confident "p=" call and NO accuracy "95% CI" lead — matching the honest
    # Memory/Performance/Readiness bands beneath it instead of printing a
    # confident verdict from the flat Beta(1,1) prior.
    from PyQt6.QtWidgets import QLabel

    col = _empty_col()
    deck = _seed(col, "los::topica", n_cards=2, reviews_each=1, frac_ok=1.0)
    # Precondition: the give-up rule actually fires for this deck.
    assert anki_cfa.memory_score(col, deck_id=deck).abstain
    mw = _StandInMW(col)
    dlg = cfa.ExamReadinessDialog(mw, deck)  # type: ignore[arg-type]

    text = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
    assert "keep studying" in text.lower()
    assert "p=" not in text, "abstaining hero must not print a p= probability"
    assert "likely pass" not in text and "likely fail" not in text
    assert "95% CI" not in text, "abstaining hero must not show the accuracy CI"
    # The honesty caveat is still present.
    assert "not validated against real exam data" in text
    dlg.close()
    col.close()


def test_dialog_hero_shows_call_above_giveup_threshold() -> None:
    # item3 sub-bug 3A — the complement: with enough graded reviews and coverage
    # the give-up rule does NOT fire, so the confident Bayesian call is shown
    # exactly as before (p=, the 95% CI lead) and the abstain hero is absent.
    from PyQt6.QtWidgets import QLabel

    col = _empty_col()
    deck = _seed(col, "los::topica", n_cards=40, reviews_each=6, frac_ok=0.95)
    assert not anki_cfa.memory_score(col, deck_id=deck).abstain
    mw = _StandInMW(col)
    dlg = cfa.ExamReadinessDialog(mw, deck)  # type: ignore[arg-type]

    text = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
    assert ("likely pass" in text) or ("likely fail" in text)
    assert "p=" in text
    assert "95% CI" in text
    assert "keep studying" not in text.lower()
    dlg.close()
    col.close()


def test_dialog_topic_count_is_canonical_and_consistent() -> None:
    # item3 sub-bug 3B — count == table rows == list == canonical 8. With no
    # exam config the readiness scores fall back to the canonical topic list, so
    # the per-topic table, the "N/total topics" caption and score.topics all
    # resolve to the same eight authored CFA topics (and the dialog renders
    # without the old no-config crash).
    from PyQt6.QtWidgets import QLabel, QTableWidget

    col = _empty_col()
    deck = _seed(
        col, "los::ethics", n_cards=5, reviews_each=3, frac_ok=0.8, configure=False
    )
    assert anki_cfa.get_exam_config(col) is None
    score = anki_cfa.memory_score(col, deck_id=deck)
    assert score.topics_total == 8
    assert len(score.topics) == 8

    mw = _StandInMW(col)
    dlg = cfa.ExamReadinessDialog(mw, deck)  # type: ignore[arg-type]
    table = dlg.findChild(QTableWidget)
    assert table is not None
    assert table.rowCount() == 8, (
        "per-topic table must have one row per canonical topic"
    )

    text = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
    assert "/8 topics" in text, "caption must count against the canonical 8"
    dlg.close()
    col.close()


def test_readiness_abstain_html_pure() -> None:
    html = cfa._readiness_abstain_html(
        "not enough data: 2 graded reviews (need 200), 100% topic coverage (need 50%)"
    )
    assert "keep studying" in html.lower()
    assert "p=" not in html
    assert "95% CI" not in html
    assert "not enough data" in html.lower()
    # Give-up reason is surfaced and the standing caveat is kept.
    assert "2 graded reviews" in html
    assert "not validated against real exam data" in html


def test_readiness_call_html_pure() -> None:
    class _R:
        call = "likely fail"
        call_prob = 0.71
        accuracy = 0.42
        ci_low = 0.10
        ci_high = 0.74
        mps = 0.65
        recall = 0.55
        first_exposures = 12
        topics_covered = 1
        topics_total = 3
        label = "not validated against real exam data"

    html = cfa._readiness_call_html(_R())
    assert "likely fail" in html
    assert "p=0.71" in html
    assert "95% CI" in html
    assert "est. recall" in html
    assert "not validated against real exam data" in html
