# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Increment 3 (desktop-shell): the top toolbar reads as a CFA product.

The center links are Home / Study / Ethics / Readiness (delegating to the CFA
entry points), Sync is preserved (its load-bearing id), and the Anki-centric
Add / Browse / Stats links are gone from the top bar. Fails on stock Anki.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt.toolbar import Toolbar

_REPO = Path(__file__).resolve().parents[2]


def _toolbar() -> Toolbar:
    # Toolbar.__init__ only stores mw/web and sets web.requiresCol — no Qt needed.
    web = SimpleNamespace(requiresCol=True)
    mw = SimpleNamespace()
    return Toolbar(mw, web)  # type: ignore[arg-type]


def _center_links_src() -> str:
    src = (_REPO / "qt" / "aqt" / "toolbar.py").read_text(encoding="utf-8")
    start = src.index("def _centerLinks")
    end = src.index("\n    def ", start + 1)
    return src[start:end]


def test_cfa_link_html_shape() -> None:
    # create_link renders the anchor + registers the click handler (no tr needed
    # for our literal-label links).
    tb = _toolbar()
    html = tb.create_link(
        "cfa_home", "Home", tb._cfaHomeLinkHandler, tip="CFA Home", id="cfa_home"
    )
    assert "pycmd('cfa_home')" in html
    assert 'id="cfa_home"' in html
    assert "Home" in html
    assert tb.link_handlers["cfa_home"] == tb._cfaHomeLinkHandler


def test_center_links_reframed_to_cfa() -> None:
    body = _center_links_src()
    for cmd in ("cfa_home", "cfa_study", "cfa_ethics", "cfa_readiness"):
        assert f'"{cmd}"' in body, f"missing CFA center link {cmd}"
    # Sync stays (its id is load-bearing for toolbar.ts / set_sync_status).
    assert "_create_sync_link()" in body


def test_anki_center_links_removed_from_top_bar() -> None:
    body = _center_links_src()
    for gone in ('"decks"', '"add"', '"browse"', '"stats"'):
        assert gone not in body, f"stock Anki center link still present: {gone}"


def test_cfa_link_handlers_exist() -> None:
    for name in (
        "_cfaHomeLinkHandler",
        "_cfaStudyLinkHandler",
        "_cfaEthicsLinkHandler",
        "_cfaReadinessLinkHandler",
    ):
        assert callable(getattr(Toolbar, name))


# --- clunky Connect/Logout redesign: one context-aware account control -------


def test_account_link_spec_logged_out_is_connect() -> None:
    from aqt.cfa_sync_connect import account_link_spec

    spec = account_link_spec(False)
    assert spec["cmd"] == "cfa_sync_settings"
    assert spec["label"] == "Connect & Sync"
    assert spec["id"] == "cfa_account"


def test_account_link_spec_logged_in_is_logout_naming_account() -> None:
    from aqt.cfa_sync_connect import account_link_spec

    spec = account_link_spec(True, "cfa")
    assert spec["cmd"] == "cfa_sync_settings"
    assert spec["label"] == "Sync settings"
    assert spec["id"] == "cfa_account"
    # the tip names the signed-in account so it's clear WHICH login is managed
    assert "cfa" in spec["tip"]


def test_account_link_spec_logged_in_without_name_is_safe() -> None:
    from aqt.cfa_sync_connect import account_link_spec

    spec = account_link_spec(True, None)
    assert spec["cmd"] == "cfa_sync_settings"
    assert "your sync account" in spec["tip"]


def _toolbar_with_auth(logged_in: bool, user: str | None) -> Toolbar:
    tb = _toolbar()
    hkey = "HKEY" if logged_in else None
    tb.mw.pm = SimpleNamespace(  # type: ignore[attr-defined]
        sync_auth=lambda: object() if hkey else None,
        profile={"syncUser": user},
    )
    return tb


def test_create_account_link_flips_with_login_state() -> None:
    # logged out -> the single control is Connect & Sync, wired to settings/status
    out = _toolbar_with_auth(False, None)
    html = out._create_account_link()
    assert "pycmd('cfa_sync_settings')" in html
    assert 'id="cfa_account"' in html
    assert ">Connect & Sync</a>" in html
    assert out.link_handlers["cfa_sync_settings"] == out._cfaSyncSettingsLinkHandler

    # logged in -> the SAME control opens status/settings; logout lives inside.
    inn = _toolbar_with_auth(True, "cfa")
    html2 = inn._create_account_link()
    assert "pycmd('cfa_sync_settings')" in html2
    assert 'id="cfa_account"' in html2
    assert ">Sync settings</a>" in html2
    assert inn.link_handlers["cfa_sync_settings"] == inn._cfaSyncSettingsLinkHandler


def test_center_links_builds_single_account_control() -> None:
    # The old clunky pair of always-visible create_link("cfa_connect") +
    # create_link("cfa_logout") is gone; exactly one settings/status chip is
    # appended after Sync.
    body = _center_links_src()
    assert "_create_account_link()" in body
    assert '"cfa_connect"' not in body
    assert '"cfa_logout"' not in body
