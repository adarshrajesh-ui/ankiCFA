# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Increment 4 (desktop-shell): the CFA design system re-skins the stock chrome.

The top toolbar and the deck list get the CFA palette/type (parity with the
SvelteKit pages) via public gui_hooks — no stock render code is rewritten.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt import cfa_chrome, cfa_style


# Stand-ins whose class __name__ matches the real contexts cfa_chrome detects.
class TopToolbar:
    pass


class DeckBrowser:
    pass


def test_toolbar_gets_cfa_skin() -> None:
    wc = SimpleNamespace(head="", body="<div class='header'></div>")
    cfa_chrome.on_webview_will_set_content(wc, TopToolbar())
    assert "cfa-chrome-toolbar" in wc.head
    # parity palette: brand navy + warm accent from the locked TOKENS
    assert cfa_style.TOKENS["accent"].lower() in wc.head.lower()
    assert ".hitem" in wc.head


def test_deckbrowser_gets_cfa_skin_and_banner() -> None:
    body = "<table><tr><td>Default</td></tr></table>"
    wc = SimpleNamespace(head="", body=body)
    cfa_chrome.on_webview_will_set_content(wc, DeckBrowser())
    assert "cfa-chrome-deckbrowser" in wc.head
    # brand banner is prepended above the deck table
    assert "cfa-deck-banner" in wc.body
    assert wc.body.index("cfa-deck-banner") < wc.body.index("<table")


def test_other_contexts_untouched() -> None:
    wc = SimpleNamespace(head="", body="x")
    cfa_chrome.on_webview_will_set_content(wc, object())
    assert wc.head == ""
    assert wc.body == "x"


def test_deck_browser_render_hook_adds_caption() -> None:
    content = SimpleNamespace(tree="<tree>", stats="<stats>")
    cfa_chrome.on_deck_browser_will_render_content(SimpleNamespace(), content)
    assert "cfa-deck-caption" in content.stats
    assert content.tree == "<tree>"  # tree (inside <table>) left intact


def test_register_is_idempotent() -> None:
    from aqt import gui_hooks

    cfa_chrome._registered = False
    before = len(gui_hooks.webview_will_set_content._hooks)
    cfa_chrome.register()
    cfa_chrome.register()
    after = len(gui_hooks.webview_will_set_content._hooks)
    assert after == before + 1  # registered exactly once despite two calls
