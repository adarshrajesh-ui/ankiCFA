# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""In-app AI settings — the visible desktop control for the CFA AI toggles.

Reads/writes the shared AI-toggle contract in ``col.conf``:

* ``cfa_ai_enabled``          — master switch (default OFF)
* ``cfa_ai_grading_enabled``  — AI semantic ethics grading
* ``cfa_ai_tabfill_enabled``  — AI tab-to-fill (draft the Back field)

AI runs for a feature only when the master switch AND that feature toggle are on
AND an OpenAI API key is configured; otherwise the feature uses its deterministic
fallback. This module owns the UI + persistence only — the AI modules read these
keys through their own gate (never touched here). Defaults are ON (AI-first): with
a key, ethics grading + tab-fill use the model out of the box; without a key,
every feature still degrades deterministically.
"""

from __future__ import annotations

from typing import Callable

from aqt.qt import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    qconnect,
)

CFA_AI_MASTER = "cfa_ai_enabled"
CFA_AI_GRADING = "cfa_ai_grading_enabled"
CFA_AI_TABFILL = "cfa_ai_tabfill_enabled"


def get_ai_toggles(col) -> dict[str, bool]:
    """Read the three AI toggles (all default ON — AI-first).

    AI is default-ON so ethics grading + tab-fill use the model out of the box;
    without an API key every feature still degrades to its deterministic
    fallback, and any switch can be turned off here."""
    return {
        "master": bool(col.get_config(CFA_AI_MASTER, True)),
        "grading": bool(col.get_config(CFA_AI_GRADING, True)),
        "tabfill": bool(col.get_config(CFA_AI_TABFILL, True)),
    }


def set_ai_toggles(col, *, master: bool, grading: bool, tabfill: bool) -> None:
    """Persist the three AI toggles to col.conf (syncs with the collection)."""
    col.set_config(CFA_AI_MASTER, bool(master))
    col.set_config(CFA_AI_GRADING, bool(grading))
    col.set_config(CFA_AI_TABFILL, bool(tabfill))


def ai_active(col, feature: str) -> bool:
    """Whether a feature's AI path is *enabled by the toggles* (master AND
    feature). Key presence is checked separately by the AI modules — this mirrors
    the contract's toggle half so the UI/tests agree on the rule."""
    t = get_ai_toggles(col)
    return t["master"] and t.get(feature, False)


class CfaAiSettingsDialog(QDialog):
    """A small CFA-branded dialog with the master + per-feature AI switches."""

    def __init__(self, mw, on_saved: Callable[[], None] | None = None) -> None:
        super().__init__(mw)
        self.mw = mw
        self._on_saved = on_saved
        self.setWindowTitle("ankiCFA — AI settings")
        self.setMinimumWidth(420)

        cur = get_ai_toggles(mw.col)
        self.master_cb = QCheckBox("Enable AI features (master switch)")
        self.master_cb.setChecked(cur["master"])
        self.grading_cb = QCheckBox("AI semantic ethics grading")
        self.grading_cb.setChecked(cur["grading"])
        self.tabfill_cb = QCheckBox("AI tab-to-fill (draft the Back field)")
        self.tabfill_cb.setChecked(cur["tabfill"])

        qconnect(self.master_cb.toggled, self._sync_enabled)
        self._sync_enabled()

        note = QLabel(
            "AI runs for a feature only when the master switch AND that feature "
            "are on AND an OpenAI API key is configured. Otherwise every feature "
            "uses its deterministic fallback — identical, offline behaviour. "
            "AI is on by default."
        )
        note.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        qconnect(buttons.accepted, self.accept)
        qconnect(buttons.rejected, self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.master_cb)
        layout.addWidget(self.grading_cb)
        layout.addWidget(self.tabfill_cb)
        layout.addWidget(note)
        layout.addWidget(buttons)
        self.setLayout(layout)

        # CFA-brand the dialog chrome (best-effort; never raises).
        try:
            from aqt.cfa_style import apply as _apply_cfa

            _apply_cfa(self)
        except Exception:
            pass

    def _sync_enabled(self) -> None:
        on = self.master_cb.isChecked()
        self.grading_cb.setEnabled(on)
        self.tabfill_cb.setEnabled(on)

    def accept(self) -> None:
        set_ai_toggles(
            self.mw.col,
            master=self.master_cb.isChecked(),
            grading=self.grading_cb.isChecked(),
            tabfill=self.tabfill_cb.isChecked(),
        )
        if self._on_saved is not None:
            try:
                self._on_saved()
            except Exception:
                pass
        super().accept()


def open_ai_settings(mw) -> None:
    """Open the AI settings dialog; refresh CFA Home so its AI chip updates."""

    def _refresh() -> None:
        if getattr(mw, "state", None) == "cfaHome":
            mw.moveToState("cfaHome")

    CfaAiSettingsDialog(mw, on_saved=_refresh).exec()
