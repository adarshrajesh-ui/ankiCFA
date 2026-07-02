# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Feature 4: the CFA desktop menu exposes four study actions.

Builds the real ``aqt.cfa`` menu against a lightweight QWidget stand-in for the
main window and asserts the menu wiring, without needing a full AnkiQt/profile.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMenuBar, QWidget

from aqt import cfa

# Hold a module-level reference so the QApplication is not garbage-collected
# (a dropped reference destroys the C++ instance and aborts on the next QWidget).
_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication(["test"])  # type: ignore[assignment]
    return _APP  # type: ignore[return-value]


def _make_menu() -> "tuple[QWidget, object]":
    _app()
    mw = QWidget()
    mw.form = SimpleNamespace(menubar=QMenuBar())  # type: ignore[attr-defined]
    cfa.setup_menu(mw)  # type: ignore[arg-type]
    return mw, mw._cfa_menu  # type: ignore[attr-defined]


def test_cfa_menu_has_four_actions() -> None:
    _mw, menu = _make_menu()
    actions = menu.actions()
    assert len(actions) == 4


def test_cfa_menu_action_labels() -> None:
    _mw, menu = _make_menu()
    labels = [a.text() for a in menu.actions()]
    assert labels == [
        "Exam Readiness…",
        "Study Ethics Minimal-Pairs",
        "Study by Exam Priority",
        "Peak-on-Exam-Day (Deadline)…",
    ]


def test_cfa_menu_handlers_exist() -> None:
    # Every advertised action maps to a real, callable handler.
    for name in (
        "show_exam_readiness",
        "study_ethics_pairs",
        "study_by_exam_priority",
        "show_deadline",
    ):
        assert callable(getattr(cfa, name))
