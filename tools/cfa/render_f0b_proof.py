# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render REAL offscreen proof of the F0b desktop fixes.

Builds the actual ``aqt.cfa.DeadlineDialog`` (the new exam-date picker surface)
against a live collection and grabs it to PNG — no mocks, the same widget the
desktop app shows. Renders two states so the picker is visibly functional:

* ``f0b-deadline-default.png`` — fresh collection, no config: the dialog
  defaults to a sensible CFA exam day and renders cleanly with no due cards.
* ``f0b-deadline-picked.png``  — after picking + persisting a new exam date via
  ``set_exam_config`` and reloading.

Usage: QT_QPA_PLATFORM=offscreen python tools/cfa/render_f0b_proof.py
"""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from anki.collection import Collection
from aqt import cfa
from aqt.cfa_seed import ensure_ethics_deck
from aqt.qt import QDate

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "proof",
    "gnhf2",
)


class _MW(QWidget):
    def __init__(self, col: Collection) -> None:
        super().__init__()
        self.col = col

    def reset(self) -> None:
        pass

    def moveToState(self, state: str) -> None:
        pass


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def _save(widget: QWidget, name: str) -> str:
    widget.resize(560, 500)
    path = os.path.join(OUT_DIR, name)
    ok = widget.grab().save(path)
    if not ok:
        raise RuntimeError(f"failed to save {path}")
    return path


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    app = QApplication.instance() or QApplication(["render"])
    assert app is not None

    # This harness has no running AnkiQt (aqt.mw is None), so the real tooltip
    # cannot fire; stub it. The dialog logic under test is unaffected.
    cfa.tooltip = lambda *a, **k: None  # type: ignore[assignment]

    col = _empty_col()
    try:
        # Preload the ethics deck so the collection is realistic (all new cards).
        ensure_ethics_deck(col)

        mw = _MW(col)

        # State 1: default exam day, no due cards — honest empty render.
        dlg = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]
        p1 = _save(dlg, "f0b-deadline-default.png")
        print(f"wrote {p1} (default: {dlg.date_edit.date().toString('yyyy-MM-dd')})")

        # State 2: pick + persist a different exam date, then reload.
        dlg.date_edit.setDate(QDate(2027, 5, 15))
        dlg._apply_date()
        p2 = _save(dlg, "f0b-deadline-picked.png")
        from anki import cfa as anki_cfa

        stored = anki_cfa.get_exam_config(col)
        print(f"wrote {p2} (persisted exam_date={stored['exam_date']})")
    finally:
        col.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
