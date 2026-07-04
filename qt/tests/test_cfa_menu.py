# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Feature 4: the CFA desktop menu exposes its study actions.

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


def test_cfa_menu_has_eight_actions() -> None:
    _mw, menu = _make_menu()
    actions = menu.actions()
    assert len(actions) == 8


def test_cfa_menu_action_labels() -> None:
    _mw, menu = _make_menu()
    labels = [a.text() for a in menu.actions()]
    assert labels == [
        "CFA Home",
        "Exam Readiness…",
        "Study Ethics Minimal-Pairs",
        "Study by Exam Priority",
        "Peak-on-Exam-Day (Deadline)…",
        "AI Settings…",
        "Connect to CFA Sync server",
        "Log out of Sync…",
    ]


def test_cfa_menu_has_logout_entry_and_handler() -> None:
    from aqt import cfa as cfa_mod

    _mw, menu = _make_menu()
    labels = [a.text() for a in menu.actions()]
    assert "Log out of Sync…" in labels
    assert callable(cfa_mod.logout_of_sync)


def test_toolbar_exposes_logout_link() -> None:
    # The always-visible top bar carries a "Log out" entry right after Sync,
    # wired to the shared public logout handler.
    from aqt import cfa as cfa_mod
    from aqt.toolbar import Toolbar

    assert callable(getattr(Toolbar, "_cfaLogoutLinkHandler", None))
    assert callable(cfa_mod.logout_of_sync)


def test_toolbar_and_menu_expose_connect_sync() -> None:
    # One-click "Connect" (top bar) + "Connect to CFA Sync server" (menu) both
    # route to the shared one-click connector.
    from aqt.cfa_sync_connect import connect_cfa_sync
    from aqt.toolbar import Toolbar

    assert callable(getattr(Toolbar, "_cfaConnectLinkHandler", None))
    assert callable(connect_cfa_sync)

    _mw, menu = _make_menu()
    labels = [a.text() for a in menu.actions()]
    assert "Connect to CFA Sync server" in labels


def test_connect_cfa_sync_configures_and_syncs(monkeypatch) -> None:
    # connect_cfa_sync points the profile at the CFA server, logs in (storing the
    # minted hkey + username), and kicks off the normal GUI sync.
    from aqt import cfa_sync_connect as cc
    import aqt.utils as u

    monkeypatch.setattr(u, "tooltip", lambda *a, **k: None)
    monkeypatch.setattr(u, "showWarning", lambda *a, **k: None)

    calls: dict = {}

    class Col:
        def sync_login(self, user, password, endpoint):
            calls["login"] = (user, password, endpoint)
            return SimpleNamespace(hkey="HKEY123")

    class PM:
        def set_custom_sync_url(self, url):
            calls["url"] = url

        def set_sync_key(self, key):
            calls["key"] = key

        def set_sync_username(self, name):
            calls["user"] = name

    class MW:
        pm = PM()
        col = Col()

        def on_sync_button_clicked(self):
            calls["synced"] = True

    cc.connect_cfa_sync(MW())  # type: ignore[arg-type]
    assert calls["url"] == cc.CFA_SYNC_URL
    assert calls["login"] == (cc.CFA_SYNC_USER, cc.CFA_SYNC_PASS, cc.CFA_SYNC_URL)
    assert calls["key"] == "HKEY123"
    assert calls["user"] == cc.CFA_SYNC_USER
    assert calls.get("synced") is True


def test_cfa_menu_single_ethics_entry_is_minimal_pairs() -> None:
    # The menu is consistent with the CFA Home CTAs: one ethics entry, the
    # Minimal-Pairs flagship. The one-passage drill is retired from the menu.
    _mw, menu = _make_menu()
    labels = [a.text() for a in menu.actions()]
    assert "Study Ethics Minimal-Pairs" in labels
    assert "Study Ethics (One-Passage)" not in labels


def test_cfa_menu_has_home_entry() -> None:
    _mw, menu = _make_menu()
    labels = [a.text() for a in menu.actions()]
    assert "CFA Home" in labels


def test_cfa_menu_handlers_exist() -> None:
    # Every advertised action maps to a real, callable handler.
    for name in (
        "show_exam_readiness",
        "study_ethics_pairs",
        "study_ethics_passages",
        "study_by_exam_priority",
        "show_deadline",
    ):
        assert callable(getattr(cfa, name))


def test_logout_clears_auth_when_confirmed(monkeypatch) -> None:
    from aqt import cfa as cfa_mod
    import aqt.utils as u

    monkeypatch.setattr(u, "askUser", lambda *a, **k: True)
    monkeypatch.setattr(u, "tooltip", lambda *a, **k: None)
    monkeypatch.setattr(u, "showInfo", lambda *a, **k: None)
    cleared: list = []

    class PM:
        profile = {"syncUser": "cfa@example.com"}

        def sync_auth(self):
            return object()  # logged in

        def clear_sync_auth(self):
            cleared.append(True)

    class Media:
        def force_resync(self):
            pass

    mw = SimpleNamespace(pm=PM(), col=SimpleNamespace(media=Media()))
    cfa_mod.logout_of_sync(mw)  # type: ignore[arg-type]
    assert cleared == [True]


def test_logout_noop_when_not_logged_in(monkeypatch) -> None:
    from aqt import cfa as cfa_mod
    import aqt.utils as u

    info: list = []
    monkeypatch.setattr(u, "showInfo", lambda *a, **k: info.append(True))

    def _no_ask(*a, **k):
        raise AssertionError("must not prompt when already logged out")

    monkeypatch.setattr(u, "askUser", _no_ask)
    cleared: list = []

    class PM:
        profile: dict = {}

        def sync_auth(self):
            return None  # not logged in

        def clear_sync_auth(self):
            cleared.append(True)

    mw = SimpleNamespace(pm=PM(), col=None)
    cfa_mod.logout_of_sync(mw)  # type: ignore[arg-type]
    assert cleared == [] and info == [True]
