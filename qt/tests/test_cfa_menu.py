# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Feature 4: the CFA desktop menu exposes its study actions.

Builds the real ``aqt.cfa`` menu against a lightweight QWidget stand-in for the
main window and asserts the menu wiring, without needing a full AnkiQt/profile.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMenuBar, QWidget

from aqt import cfa

_REPO = Path(__file__).resolve().parents[2]

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


def _command_actions(menu) -> list:
    """The invocable menu commands, excluding section-header separators (D11)."""
    return [a for a in menu.actions() if not a.isSeparator()]


def _visible_label(action) -> str:
    return action.text().replace("&&", "&")


def test_cfa_menu_has_seven_actions() -> None:
    _mw, menu = _make_menu()
    assert len(_command_actions(menu)) == 7


def test_cfa_menu_action_labels() -> None:
    _mw, menu = _make_menu()
    labels = [_visible_label(a) for a in _command_actions(menu)]
    assert labels == [
        "CFA Home",
        "Exam Readiness…",
        "Study Ethics Minimal-Pairs",
        "Study by Exam Priority",
        "Peak-on-Exam-Day (Deadline)…",
        "AI Settings…",
        "Settings & Sync…",
    ]


def test_cfa_menu_is_grouped_into_labelled_sections() -> None:
    # D11 (Phase B Pass 2): the eight commands are grouped under three labelled
    # native section separators, not a flat undifferentiated list.
    _mw, menu = _make_menu()
    sections = [a.text() for a in menu.actions() if a.isSeparator() and a.text()]
    assert sections == ["Dashboard", "Study modes", "Settings & account"]

    # Each command carries a discoverability status-tip (premium desktop hover).
    assert all(a.statusTip() for a in _command_actions(menu))


def test_cfa_menu_sections_order_commands_correctly() -> None:
    # The first non-separator after each section header belongs to that group.
    _mw, menu = _make_menu()
    order: list[tuple[str, str]] = []
    current = ""
    for a in menu.actions():
        if a.isSeparator() and a.text():
            current = a.text()
        elif not a.isSeparator():
            order.append((current, a.text()))
    assert ("Dashboard", "CFA Home") in order
    assert ("Study modes", "Study Ethics Minimal-Pairs") in order
    assert ("Settings & account", "AI Settings…") in order
    # No command leaks out ahead of the first section header.
    assert all(section for section, _ in order)


def test_cfa_menu_has_settings_sync_entry_and_logout_handler() -> None:
    from aqt import cfa as cfa_mod

    _mw, menu = _make_menu()
    labels = [_visible_label(a) for a in menu.actions()]
    assert "Settings & Sync…" in labels
    assert "Log out of Sync…" not in labels
    assert callable(cfa_mod.logout_of_sync)


def test_toolbar_exposes_sync_settings_link() -> None:
    # The public logout handler still exists, but the always-visible top bar now
    # opens the native status/settings dialog instead of showing logout chrome.
    from aqt import cfa as cfa_mod
    from aqt.toolbar import Toolbar

    assert callable(getattr(Toolbar, "_cfaSyncSettingsLinkHandler", None))
    assert callable(cfa_mod.logout_of_sync)


def test_toolbar_and_menu_expose_connect_sync() -> None:
    # One-click connect still exists, but the visible chrome is now the native
    # Settings & Sync entry so setup/status/logout are one CFA flow.
    from aqt.cfa_sync_connect import connect_cfa_sync
    from aqt.toolbar import Toolbar

    assert callable(getattr(Toolbar, "_cfaConnectLinkHandler", None))
    assert callable(getattr(Toolbar, "_cfaSyncSettingsLinkHandler", None))
    assert callable(connect_cfa_sync)

    _mw, menu = _make_menu()
    labels = [_visible_label(a) for a in menu.actions()]
    assert "Settings & Sync…" in labels


def test_connect_cfa_sync_uses_normal_anki_sync(monkeypatch) -> None:
    # connect_cfa_sync no longer points at a custom server or logs in with fixed
    # credentials: it heals any stale loopback dev URL and then drives Anki's own
    # sync flow (which handles login-if-needed).
    import aqt.utils as u
    from aqt import cfa_sync_connect as cc

    monkeypatch.setattr(u, "showWarning", lambda *a, **k: None)

    calls: dict = {}

    class PM:
        def __init__(self) -> None:
            self._url = "http://127.0.0.1:27701/"

        def custom_sync_url(self):
            return self._url

        def set_custom_sync_url(self, url):
            self._url = url
            calls["cleared_to"] = url

    class MW:
        pm = PM()
        col = object()

        def on_sync_button_clicked(self):
            calls["synced"] = True

    cc.connect_cfa_sync(MW())  # type: ignore[arg-type]
    # stale loopback dev URL cleared (-> AnkiWeb), then the normal sync runs
    assert calls.get("cleared_to") is None
    assert calls.get("synced") is True


def test_connect_cfa_sync_without_profile_uses_product_safe_copy(monkeypatch) -> None:
    import aqt.utils as u
    from aqt import cfa_sync_connect as cc

    warnings: list[str] = []
    monkeypatch.setattr(u, "showWarning", lambda msg, **k: warnings.append(msg))

    class MW:
        col = None

    cc.connect_cfa_sync(MW())  # type: ignore[arg-type]

    assert warnings
    _assert_no_sync_backend_terms(warnings[0])


def test_heal_stale_local_sync_url_only_clears_loopback() -> None:
    from aqt import cfa_sync_connect as cc

    class PM:
        def __init__(self, url) -> None:
            self.url = url

        def custom_sync_url(self):
            return self.url

        def set_custom_sync_url(self, url):
            self.url = url

    # a dead loopback dev URL is cleared so sync falls back to AnkiWeb
    loopback = SimpleNamespace(pm=PM("http://127.0.0.1:27701/"))
    assert cc.heal_stale_local_sync_url(loopback) is True
    assert loopback.pm.url is None

    # a genuine self-hosted server the user configured is left untouched
    custom = SimpleNamespace(pm=PM("https://sync.example.com/"))
    assert cc.heal_stale_local_sync_url(custom) is False
    assert custom.pm.url == "https://sync.example.com/"

    # AnkiWeb default (no custom url) is a no-op
    default = SimpleNamespace(pm=PM(None))
    assert cc.heal_stale_local_sync_url(default) is False


def test_sync_connection_error_message_handles_empty_endpoint() -> None:
    from aqt import cfa_sync_connect as cc

    message = cc.sync_connection_error_message("")

    assert "Settings & Sync" in message
    _assert_no_sync_backend_terms(message)


def test_sync_user_copy_hides_local_backend_details() -> None:
    from aqt import cfa_sync_connect as cc

    class PM:
        profile: dict = {}

        def sync_auth(self):
            return None

        def sync_endpoint(self):
            return "http://127.0.0.1:27701/"

    status = cc.sync_status_payload(SimpleNamespace(pm=PM()))
    strings = [
        cc.account_link_spec(False)["tip"],
        cc.sync_connection_error_message("http://127.0.0.1:27701/"),
        str(status["endpoint"]),
        str(status["detail"]),
    ]

    for text in strings:
        _assert_no_sync_backend_terms(text)
        assert "desktop" not in text.lower()


def test_sync_settings_dialog_is_phone_sized_and_touch_friendly() -> None:
    from aqt import cfa_sync_connect as cc

    assert cc.SYNC_DIALOG_MIN_WIDTH <= 320
    assert cc.SYNC_DIALOG_DEFAULT_WIDTH <= 390
    assert cc.SYNC_DIALOG_DEFAULT_WIDTH == 390
    assert cc.SYNC_DIALOG_BUTTON_MIN_HEIGHT >= 44
    assert cc.SYNC_DIALOG_SCREEN_MARGIN >= 24

    src = (_REPO / "qt" / "aqt" / "cfa_sync_connect.py").read_text(encoding="utf-8")
    start = src.index("def open_sync_settings")
    end = src.index("\n\ndef ", start + 1)
    body = src[start:end]
    assert "QHBoxLayout" not in body
    assert "QVBoxLayout" in body
    assert "_sync_dialog_width(mw)" in body
    assert "setMinimumWidth(min(" in body
    assert "setMinimumWidth(0)" in body
    assert "setMinimumSize(500" not in body
    assert "setSizeGripEnabled(True)" in body


def _assert_no_sync_backend_terms(text: str) -> None:
    lowered = text.lower()
    for forbidden in (
        "127.0.0.1",
        "localhost",
        "sync server",
        "terminal",
        "just cfa-syncserver",
        "error sending request",
        "url ()",
        "http://",
        "https://",
    ):
        assert forbidden not in lowered, f"leaked backend detail: {forbidden}"


def test_cfa_menu_single_ethics_entry_is_minimal_pairs() -> None:
    # The menu is consistent with the CFA Home CTAs: one ethics entry, the
    # Minimal-Pairs flagship. The one-passage drill is retired from the menu.
    _mw, menu = _make_menu()
    labels = [_visible_label(a) for a in menu.actions()]
    assert "Study Ethics Minimal-Pairs" in labels
    assert "Study Ethics (One-Passage)" not in labels


def test_cfa_menu_has_home_entry() -> None:
    _mw, menu = _make_menu()
    labels = [_visible_label(a) for a in menu.actions()]
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
    import aqt.utils as u
    from aqt import cfa as cfa_mod

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
    import aqt.utils as u
    from aqt import cfa as cfa_mod

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
