# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Ethics Minimal-Pairs — Anki add-on entry point.

Symlink or copy this directory into your Anki ``addons21`` folder (see README / ``just cfa-install``).
On startup it adds a Tools-menu item that opens the per-cluster discrimination dashboard in an
AnkiWebView and live-refreshes it after every review.

This module is import-safe outside Anki (e.g. under pytest): if ``aqt`` isn't importable it does
nothing, so the package can coexist with the standalone scripts and unit tests in this directory.
"""

from __future__ import annotations

try:
    from aqt import gui_hooks, mw
    from aqt.qt import QAction, QDialog, Qt, QVBoxLayout
    from aqt.webview import AnkiWebView

    _IN_ANKI = True
except Exception:  # pragma: no cover - not running inside the Anki desktop app
    _IN_ANKI = False


if _IN_ANKI:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import ethics_dashboard

    _dialog: "QDialog | None" = None

    class _DashboardDialog(QDialog):
        def __init__(self, parent) -> None:
            super().__init__(parent, Qt.WindowType.Window)
            self.setWindowTitle("CFA Ethics — Discrimination Dashboard")
            self.resize(780, 580)
            self.web = AnkiWebView(self, title="CFA Ethics Dashboard")
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.web)
            self.setLayout(layout)
            self.refresh()

        def refresh(self) -> None:
            try:
                html = ethics_dashboard.build_report(mw.col)
            except Exception as exc:  # never let a dashboard error break the reviewer
                html = f"<html><body style='font-family:sans-serif;padding:20px'>Dashboard error: {exc}</body></html>"
            self.web.setHtml(html)

        def reject(self) -> None:
            global _dialog
            if self.web is not None:
                self.web.cleanup()
                self.web = None
            _dialog = None
            super().reject()

    def _show_dashboard() -> None:
        global _dialog
        if _dialog is None:
            _dialog = _DashboardDialog(mw)
        else:
            _dialog.refresh()
        _dialog.show()
        _dialog.raise_()
        _dialog.activateWindow()

    def _on_answer(*_args, **_kwargs) -> None:
        if _dialog is not None and _dialog.isVisible():
            _dialog.refresh()

    def _install() -> None:
        action = QAction("CFA Ethics: Discrimination Dashboard", mw)
        action.triggered.connect(_show_dashboard)
        mw.form.menuTools.addAction(action)
        gui_hooks.reviewer_did_answer_card.append(_on_answer)

    gui_hooks.main_window_did_init.append(_install)
