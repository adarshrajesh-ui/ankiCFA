# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Reproducibly render the desktop CFA menu (D11 window chrome) to a PNG.

Phase-B Pass-2 desktop evidence for the D11 menu-bar surface. Builds the real
``aqt.cfa`` menu against a lightweight QWidget stand-in for the main window
(exactly as ``qt/tests/test_cfa_menu.py`` does), pops it up under the offscreen
Qt platform, and grabs it to a PNG — no live Anki launch.

Run (from the repo root)::

    QT_QPA_PLATFORM=offscreen PYTHONPATH="out/pylib:pylib:qt:out/qt" \\
        out/pyenv/bin/python tools/cfa/render_cfa_menu.py OUT.png
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMenuBar, QWidget  # noqa: E402

from aqt import cfa  # noqa: E402


def _render(out: str) -> None:
    app = QApplication.instance() or QApplication(["render"])
    mw = QWidget()
    mw.form = SimpleNamespace(menubar=QMenuBar())  # type: ignore[attr-defined]
    cfa.setup_menu(mw)  # type: ignore[arg-type]
    menu = mw._cfa_menu  # type: ignore[attr-defined]
    menu.popup(QPoint(0, 0))
    app.processEvents()
    menu.grab().save(out)
    menu.hide()
    print("saved", out)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "cfa-menu.png"
    _render(out)
    # Do not hold the QApplication past exit; offscreen has no event loop.
    app = QApplication.instance()
    if app is not None:
        app.quit()
