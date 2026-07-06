# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Increment 5 (desktop-shell): the in-app AI toggle UI (D3b).

The AI settings dialog reads/writes the shared col.conf toggle contract
(cfa_ai_enabled master + cfa_ai_grading_enabled + cfa_ai_tabfill_enabled) and
persists it; the per-feature switches are gated on the master. Fails on stock
    EthosPrep (no such control / keys).
"""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from anki.collection import Collection
from aqt import cfa_ai_settings as ai

_APP: QApplication | None = None
_MWS: list[QWidget] = []  # keep stand-in windows alive (avoid C++ GC aborts)


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication(["test"])  # type: ignore[assignment]
    return _APP  # type: ignore[return-value]


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


class _MW(QWidget):
    def __init__(self, col: Collection) -> None:
        super().__init__()
        self.col = col
        self.state = "cfaHome"


def _mw(col: Collection) -> _MW:
    _app()
    w = _MW(col)
    _MWS.append(w)
    return w


def test_defaults_all_on() -> None:
    # AI-first: with no keys set, all toggles read ON (a key is still required
    # for a real call; without one the features fall back deterministically).
    col = _empty_col()
    try:
        assert ai.get_ai_toggles(col) == {
            "master": True,
            "grading": True,
            "tabfill": True,
        }
    finally:
        col.close()


def test_set_toggles_persist() -> None:
    col = _empty_col()
    try:
        ai.set_ai_toggles(col, master=True, grading=True, tabfill=False)
        assert ai.get_ai_toggles(col) == {
            "master": True,
            "grading": True,
            "tabfill": False,
        }
    finally:
        col.close()


def test_ai_active_requires_master_and_feature() -> None:
    col = _empty_col()
    try:
        ai.set_ai_toggles(col, master=False, grading=True, tabfill=True)
        assert ai.ai_active(col, "grading") is False  # master off wins
        ai.set_ai_toggles(col, master=True, grading=True, tabfill=False)
        assert ai.ai_active(col, "grading") is True
        assert ai.ai_active(col, "tabfill") is False  # feature off
    finally:
        col.close()


def test_dialog_reads_and_writes() -> None:
    col = _empty_col()
    try:
        ai.set_ai_toggles(col, master=True, grading=False, tabfill=True)
        dlg = ai.CfaAiSettingsDialog(_mw(col))
        assert dlg.master_cb.isChecked() is True
        assert dlg.grading_cb.isChecked() is False
        assert dlg.tabfill_cb.isChecked() is True

        dlg.master_cb.setChecked(False)
        dlg.grading_cb.setChecked(True)
        dlg.accept()
        assert ai.get_ai_toggles(col) == {
            "master": False,
            "grading": True,
            "tabfill": True,
        }
    finally:
        col.close()


def test_feature_toggles_gated_on_master() -> None:
    col = _empty_col()
    try:
        ai.set_ai_toggles(col, master=False, grading=False, tabfill=False)
        dlg = ai.CfaAiSettingsDialog(_mw(col))
        assert dlg.grading_cb.isEnabled() is False
        assert dlg.tabfill_cb.isEnabled() is False
        dlg.master_cb.setChecked(True)
        assert dlg.grading_cb.isEnabled() is True
        assert dlg.tabfill_cb.isEnabled() is True
    finally:
        col.close()


def test_feature_group_container_gated_on_master() -> None:
    # Pass-2 redesign: the two per-feature switches live in one indented
    # container that greys out as a group when the master is off (visible
    # parent/child relationship, not just two independently-disabled rows).
    col = _empty_col()
    try:
        ai.set_ai_toggles(col, master=False, grading=True, tabfill=True)
        dlg = ai.CfaAiSettingsDialog(_mw(col))
        assert dlg._features.isEnabled() is False
        dlg.master_cb.setChecked(True)
        assert dlg._features.isEnabled() is True
    finally:
        col.close()


def test_status_html_reflects_key_presence() -> None:
    # The live key-status line states the real behaviour up front: with a key,
    # AI runs (pass tone); without one, every feature falls back (warn tone).
    present = ai.CfaAiSettingsDialog._status_html(True)
    absent = ai.CfaAiSettingsDialog._status_html(False)
    assert "detected" in present.lower()
    assert "no openai api key" in absent.lower()
    assert "fallback" in absent.lower()
    # never leak or invent a key value
    assert "sk-" not in present and "sk-" not in absent


def test_dialog_has_brand_heading() -> None:
    # Pass-2 redesign: the dialog carries the CFA brand eyebrow + serif title
    # so it reads as one product, not a generic add-on sheet.
    from PyQt6.QtWidgets import QLabel

    col = _empty_col()
    try:
        dlg = ai.CfaAiSettingsDialog(_mw(col))
        texts = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel)).lower()
        assert "ai features" in texts
        assert "ethosprep" in texts
    finally:
        col.close()
