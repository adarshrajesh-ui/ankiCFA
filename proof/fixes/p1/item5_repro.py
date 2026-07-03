#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""item5 repro — the two "Peak-on-Exam-Day" (MEDIUM #8) defects.

5B (empty table on a fresh profile): on a fresh profile whose cards are all NEW,
    the ranking the desktop dialog uses (``cfa_deadline.deadline_retention``)
    considers only DUE cards, so it returns an EMPTY ranking and the dialog
    shows "No due cards to rank yet".

5A (absurd persisted exam date): an absurd far-future persisted exam date
    (2028-08-23) is trusted verbatim by the DeadlineDialog's exam-date picker —
    there is no self-heal back to the canonical near date.

Pass ``--after`` to exercise the FIXED paths (the pylib wrapper +
self-heal) instead of the broken ones.

Run:
  QT_QPA_PLATFORM=offscreen PYTHONPATH="out/pylib:pylib:qt:out/qt" \
    out/pyenv/bin/python proof/fixes/p1/item5_repro.py [--after]
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QTableWidget, QWidget

from anki import cfa as anki_cfa
from anki import cfa_deadline
from anki.collection import Collection
from aqt import cfa

_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication(["repro"])  # type: ignore[assignment]
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


def _add_new_cards(col: Collection, deck_name: str, n: int) -> int:
    nt = col.models.by_name("Basic")
    deck = col.decks.id(deck_name)
    for i in range(n):
        note = col.new_note(nt)
        note["Front"] = f"q{i}"
        note["Back"] = "a"
        note.tags = ["los::ethics"]
        col.add_note(note, deck)
    return deck


def main() -> int:
    after = "--after" in sys.argv
    tag = "AFTER (fixed)" if after else "BEFORE (broken)"
    col = _empty_col()
    deck = _add_new_cards(col, "CFA", 6)
    col.decks.set_current(deck)

    print(f"== item5 {tag} ==")
    print(f"deck cards total   : {len(col.find_cards('deck:CFA'))}")
    print(f"deck cards is:new  : {len(col.find_cards('deck:CFA is:new'))}")
    print(f"deck cards is:due  : {len(col.find_cards('deck:CFA is:due'))}")

    # --- 5B: does the ranking include NEW cards? ---------------------------
    if after:
        res = anki_cfa.deadline_retention_with_new(
            col, deck_id=deck, exam_date="2026-08-25", fetch_limit=50
        )
        label = "anki.cfa.deadline_retention_with_new (wrapper)"
    else:
        res = cfa_deadline.deadline_retention(
            col, deck_id=deck, exam_date="2026-08-25", fetch_limit=50
        )
        label = "cfa_deadline.deadline_retention (due-only)"
    print(f"\n[5B] {label} on all-NEW deck:")
    print(f"     ranked cards = {len(res)}")
    if len(res):
        print(f"     recall of first (weakest) = {res.predicted_recall[0]}")
        print(
            f"     all recalls in [0,1]       = "
            f"{all(0.0 <= r <= 1.0 for r in res.predicted_recall)}"
        )
        print(
            f"     weakest-first (ascending)  = "
            f"{res.predicted_recall == sorted(res.predicted_recall)}"
        )

    # The real dialog: header + table.
    mw = _StandInMW(col)
    dlg = cfa.DeadlineDialog(mw)
    header = " ".join(l.text() for l in dlg.findChildren(QLabel))
    table = dlg.findChild(QTableWidget)
    assert table is not None
    print(f"     dialog table rowCount           = {table.rowCount()}")
    print(f"     dialog 'No cards to rank' notice = {'to rank yet' in header}")
    print(f"     dialog header mentions new cards = {'new' in header.lower()}")
    dlg.close()

    # --- 5A: absurd persisted exam date ------------------------------------
    anki_cfa.set_exam_config(col, exam_date="2028-08-23", topic_weights={})
    mw2 = _StandInMW(col)
    dlg2 = cfa.DeadlineDialog(mw2)
    shown = dlg2.date_edit.date().toString("yyyy-MM-dd")
    print("\n[5A] persisted exam_date = 2028-08-23 (absurd far-future pollution)")
    print(f"     DeadlineDialog picker shows = {shown}")
    print(f"     canonical default           = {cfa._default_exam_date()}")
    print(f"     used verbatim (no self-heal)= {shown == '2028-08-23'}")
    dlg2.close()

    col.close()
    print(f"\n== END item5 {tag} ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
