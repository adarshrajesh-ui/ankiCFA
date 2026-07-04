# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Increment 1 (desktop-shell): the desktop app reads as ankiCFA, not Anki.

Covers the window-title helper, the Qt application/desktop identity + startup
banner, and the CFA window-icon asset and its .ui reference. Every assertion
here fails on stock Anki and passes once the CFA branding lands.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# qt/tests/test_cfa_branding.py -> parents[2] == repo root
_REPO = Path(__file__).resolve().parents[2]


def test_window_title_includes_profile() -> None:
    from aqt.main import AnkiQt

    stub = SimpleNamespace(pm=SimpleNamespace(name="User 1"))
    assert AnkiQt.window_title(stub) == "ankiCFA - User 1"


def test_window_title_without_profile() -> None:
    from aqt.main import AnkiQt

    assert AnkiQt.window_title(SimpleNamespace(pm=None)) == "ankiCFA"
    assert AnkiQt.window_title(SimpleNamespace()) == "ankiCFA"


def test_application_identity_is_cfa() -> None:
    src = (_REPO / "qt" / "aqt" / "__init__.py").read_text(encoding="utf-8")
    assert 'setApplicationName("ankiCFA")' in src
    assert 'setDesktopFileName("ankicfa")' in src
    assert "Starting ankiCFA" in src


def test_window_icon_asset_and_reference() -> None:
    icon = _REPO / "qt" / "aqt" / "data" / "qt" / "icons" / "cfa.png"
    assert icon.is_file() and icon.stat().st_size > 0

    ui = (_REPO / "qt" / "aqt" / "forms" / "main.ui").read_text(encoding="utf-8")
    assert ":/icons/cfa.png" in ui
    assert ":/icons/anki.png" not in ui
