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
    QFrame,
    QLabel,
    Qt,
    QVBoxLayout,
    QWidget,
    qconnect,
)

CFA_AI_MASTER = "cfa_ai_enabled"
CFA_AI_GRADING = "cfa_ai_grading_enabled"
CFA_AI_TABFILL = "cfa_ai_tabfill_enabled"


def _api_key_present() -> bool:
    """Whether an OpenAI key is configured right now (best-effort, never raises).

    The dialog surfaces this so the user can tell whether the switches below
    will actually reach the model or silently fall back — the key never appears,
    only its presence. Mirrors the exact check the AI modules gate on."""
    try:
        from cfa.ai.llm_client import key_present

        return bool(key_present())
    except Exception:
        return False


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
        self.setMinimumWidth(460)

        cur = get_ai_toggles(mw.col)

        # Brand heading (eyebrow + serif title) so the dialog reads as one CFA
        # product, not a generic add-on sheet.
        heading = self._rich_label(self._heading_html())

        # Live key-status line — the whole toggle contract hinges on whether a
        # key is present, so state it plainly instead of burying it in prose.
        self._key_present = _api_key_present()
        status = self._rich_label(self._status_html(self._key_present))

        self.master_cb = QCheckBox("Enable AI features")
        self.master_cb.setChecked(cur["master"])
        master_sub = self._rich_label(
            self._sub_html("Master switch for every AI feature below.")
        )

        self.grading_cb = QCheckBox("AI semantic ethics grading")
        self.grading_cb.setChecked(cur["grading"])
        self.tabfill_cb = QCheckBox("AI tab-to-fill (draft the Back field)")
        self.tabfill_cb.setChecked(cur["tabfill"])

        qconnect(self.master_cb.toggled, self._sync_enabled)

        # Per-feature switches, indented under a quiet section divider so their
        # parent/child relationship to the master is visible, not just implied.
        features_label = self._rich_label(self._section_html("Per feature"))
        self._features = QWidget()
        feat_layout = QVBoxLayout()
        feat_layout.setContentsMargins(18, 0, 0, 0)
        feat_layout.setSpacing(6)
        feat_layout.addWidget(self.grading_cb)
        feat_layout.addWidget(self.tabfill_cb)
        self._features.setLayout(feat_layout)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)

        note = self._rich_label(
            self._sub_html(
                "Without a key — or with any switch off — every feature uses its "
                "deterministic fallback: identical, fully offline behaviour."
            )
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        qconnect(buttons.accepted, self.accept)
        qconnect(buttons.rejected, self.reject)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(4)
        layout.addWidget(heading)
        layout.addWidget(status)
        layout.addSpacing(8)
        layout.addWidget(self.master_cb)
        layout.addWidget(master_sub)
        layout.addSpacing(6)
        layout.addWidget(features_label)
        layout.addWidget(self._features)
        layout.addSpacing(8)
        layout.addWidget(divider)
        layout.addWidget(note)
        layout.addSpacing(8)
        layout.addWidget(buttons)
        self.setLayout(layout)

        # CFA-brand the dialog chrome (best-effort; never raises).
        try:
            from aqt.cfa_style import apply as _apply_cfa

            _apply_cfa(self)
        except Exception:
            pass

        self._sync_enabled()

    @staticmethod
    def _rich_label(html: str) -> QLabel:
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def _heading_html() -> str:
        try:
            from aqt.cfa_style import page_heading

            return page_heading("ankiCFA · AI", "AI features")
        except Exception:
            return "<b>AI features</b>"

    @staticmethod
    def _section_html(text: str) -> str:
        try:
            from aqt.cfa_style import section

            return section(text)
        except Exception:
            return f"<b>{text}</b>"

    @staticmethod
    def _sub_html(text: str) -> str:
        try:
            from aqt.cfa_style import caption

            return caption(text)
        except Exception:
            return text

    @staticmethod
    def _status_html(key_present: bool) -> str:
        try:
            from aqt.cfa_style import notice

            if key_present:
                return notice(
                    "OpenAI API key detected — AI runs for the switches you enable.",
                    tone="pass",
                )
            return notice(
                "No OpenAI API key set — every feature runs its offline fallback.",
                tone="warn",
            )
        except Exception:
            return "API key detected." if key_present else "No API key set."

    def _sync_enabled(self) -> None:
        on = self.master_cb.isChecked()
        self.grading_cb.setEnabled(on)
        self.tabfill_cb.setEnabled(on)
        if hasattr(self, "_features"):
            self._features.setEnabled(on)

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
