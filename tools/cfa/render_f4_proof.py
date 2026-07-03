# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render REAL offscreen proof of the F4 honest scoring redesign.

Builds the actual ``aqt.cfa.ExamReadinessDialog`` against a live collection with
synthetic reviews and grabs it to PNG — the same widget the desktop app shows,
no mocks. Renders three states so the Bayesian band + explicit pass/fail call
are visibly working and honest:

* ``f4-readiness-sparse.png`` — only a handful of reviews: no give-up wall, the
  95% credible band is very WIDE and the call is tentative.
* ``f4-readiness-strong.png`` — many reviews, mostly correct: the band has
  NARROWED and the call is "likely pass" with a high probability.
* ``f4-readiness-weak.png``   — many reviews, mostly wrong: "likely fail".

Usage: QT_QPA_PLATFORM=offscreen python tools/cfa/render_f4_proof.py
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
OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "proof",
    "gnhf2",
)


class _MW(QWidget):
    def __init__(self, col: Collection) -> None:
        super().__init__()
        self.col = col


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def _seed(col: Collection, topic: str, n_cards: int, reviews_each: int, frac_ok: float):
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
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
    anki_cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights={topic: 1.0})
    return deck


def _save(widget: QWidget, name: str) -> str:
    widget.resize(660, 580)
    path = os.path.join(OUT_DIR, name)
    if not widget.grab().save(path):
        raise RuntimeError(f"failed to save {path}")
    return path


def _render(name: str, n_cards: int, reviews_each: int, frac_ok: float) -> None:
    col = _empty_col()
    try:
        deck = _seed(col, "los::ethics", n_cards, reviews_each, frac_ok)
        mw = _MW(col)
        dlg = cfa.ExamReadinessDialog(mw, deck)  # type: ignore[arg-type]
        b = anki_cfa.bayesian_readiness(col, deck_id=deck)
        p = _save(dlg, name)
        print(
            f"wrote {p} — {b.call} p={b.call_prob:.2f}, acc={b.accuracy:.2f} "
            f"CI[{b.ci_low:.2f},{b.ci_high:.2f}] width={b.ci_high - b.ci_low:.2f} "
            f"({b.first_exposures} first-seen)"
        )
        dlg.close()
    finally:
        col.close()


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    app = QApplication.instance() or QApplication(["render"])
    assert app is not None
    cfa.tooltip = lambda *a, **k: None  # type: ignore[assignment]

    _render("f4-readiness-sparse.png", n_cards=3, reviews_each=1, frac_ok=0.67)
    _render("f4-readiness-strong.png", n_cards=40, reviews_each=8, frac_ok=0.95)
    _render("f4-readiness-weak.png", n_cards=40, reviews_each=8, frac_ok=0.30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
