# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Reproducibly render the CFA AI-settings dialog (D6) to PNGs (offscreen).

Phase-B Pass-2 desktop evidence for the D6 AI Settings surface. Instantiates the
real ``CfaAiSettingsDialog`` under the offscreen Qt platform and grabs it to a
PNG for each state — master ON, master OFF (features greyed as a group), and the
key-present status line — with no live Anki launch.

Run (from the repo root)::

    QT_QPA_PLATFORM=offscreen PYTHONPATH="out/pylib:pylib:qt:out/qt" \\
        out/pyenv/bin/python tools/cfa/render_ai_settings.py OUTDIR

The status line reflects whether an OpenAI key is configured; the ``key-present``
capture forces that branch (``_api_key_present -> True``) so the pass-tone render
is faithful without needing a real key.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

import aqt.cfa_ai_settings as ai  # noqa: E402
from anki.collection import Collection  # noqa: E402


def _col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


class _MW(QWidget):
    def __init__(self, col: Collection) -> None:
        super().__init__()
        self.col = col
        self.state = "cfaHome"


def _grab(app: QApplication, master: bool, out: str) -> None:
    col = _col()
    try:
        ai.set_ai_toggles(col, master=master, grading=True, tabfill=True)
        dlg = ai.CfaAiSettingsDialog(_MW(col))
        dlg.resize(dlg.sizeHint())
        dlg.show()
        app.processEvents()
        dlg.grab().save(out)
        print("saved", out)
    finally:
        col.close()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    outdir = args[0] if args else "."
    os.makedirs(outdir, exist_ok=True)
    app = QApplication.instance() or QApplication(["render-ai-settings"])

    _grab(app, True, os.path.join(outdir, "d6-ai-settings-master-on.png"))
    _grab(app, False, os.path.join(outdir, "d6-ai-settings-master-off.png"))

    # Force the key-present branch so its pass-tone status line renders faithfully
    # (the line is a pure function of the boolean; no real key is used or logged).
    orig = ai._api_key_present
    ai._api_key_present = lambda: True  # type: ignore[assignment]
    try:
        _grab(app, True, os.path.join(outdir, "d6-ai-settings-key-present.png"))
    finally:
        ai._api_key_present = orig  # type: ignore[assignment]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
