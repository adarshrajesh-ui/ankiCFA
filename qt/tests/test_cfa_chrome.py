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


class Overview:
    pass


class ReviewerBottomBar:
    pass


class Editor:
    pass


class Reviewer:
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


def test_deckbrowser_retones_stock_blue_leaks() -> None:
    # D8-1 (Pass 2): stock Anki paints filtered/dynamic deck NAMES with
    # --fg-link and the "New" COUNT with --state-new (both blue). The CFA skin
    # must retone both to brand navy (parity with the mobile M6-1 fix) so the
    # deck list reads as one cohesive navy CFA product.
    css = cfa_chrome._deckbrowser_css()
    navy = cfa_style.TOKENS["ink"]
    for rule in (
        f"a.deck {{ color: {navy} !important; }}",
        f"a.deck.filtered {{ color: {navy} !important; }}",
        f".new-count {{ color: {navy} !important; }}",
    ):
        assert rule in css, f"missing rule: {rule}"


def test_deckbrowser_keeps_learn_review_count_semantics() -> None:
    # The learned Anki count colours (Learn=red / Review=green) are NOT
    # recoloured — only the stock-blue New count is retoned (matches M5-2/M6-1).
    css = cfa_chrome._deckbrowser_css()
    assert ".learn-count" not in css
    assert ".review-count" not in css


def test_overview_gets_cfa_skin_and_eyebrow() -> None:
    # The deck study-intro (Overview) shipped as pure stock Anki; the CFA skin
    # must retone it (page tint, serif title, navy "Study Now" CTA) and prepend
    # a brand eyebrow above the deck title.
    body = "<center><h3>CFA::Ethics</h3></center>"
    wc = SimpleNamespace(head="", body=body)
    cfa_chrome.on_webview_will_set_content(wc, Overview())
    assert "cfa-chrome-overview" in wc.head
    # brand eyebrow is prepended above the (centred) deck title
    assert "cfa-overview-eyebrow" in wc.body
    assert wc.body.index("cfa-overview-eyebrow") < wc.body.index("<center")


def test_overview_retones_stock_blue_study_cta_and_count() -> None:
    # The single primary CTA ("Study Now" / #study) and the "New" count were
    # stock Anki blue; the CFA skin must retone both to brand navy while leaving
    # the learned Learn=red / Review=green count semantics untouched.
    css = cfa_chrome._overview_css()
    navy = cfa_style.TOKENS["ink"]
    primary = cfa_style.TOKENS["primary"]
    assert f".new-count {{ color: {navy} !important; }}" in css
    assert f"background: {primary} !important;" in css  # #study CTA
    assert ".learn-count" not in css
    assert ".review-count" not in css


def test_reviewer_bottom_gets_cfa_skin() -> None:
    # The reviewer answer bar (Show Answer + ease buttons) shipped as pure stock
    # Anki native buttons; the CFA skin must retone the most-used study surface.
    wc = SimpleNamespace(head="", body="<center id=outer></center>")
    cfa_chrome.on_webview_will_set_content(wc, ReviewerBottomBar())
    assert "cfa-chrome-reviewer-bottom" in wc.head
    # body is left intact — the bar HTML is Anki's; only the skin is injected.
    assert wc.body == "<center id=outer></center>"


def test_reviewer_bottom_primary_and_caution_cues() -> None:
    # "Show Answer" (#ansbut) + the recommended default answer (#defease) are the
    # navy primary pill; "Again" (data-ease=1) carries a quiet fail-red caution.
    css = cfa_chrome._reviewer_bottom_css()
    primary = cfa_style.TOKENS["primary"]
    fail = cfa_style.TOKENS["fail"]
    assert "#ansbut" in css
    assert "#defease" in css
    assert f"background: {primary} !important;" in css
    assert '#middle button[data-ease="1"]:not(#defease)' in css
    assert f"border-color: {fail};" in css
    # rating tiers other than Again stay neutral — no traffic-light data-ease 2/3.
    assert 'data-ease="2"' not in css
    assert 'data-ease="3"' not in css


def test_editor_gets_cfa_skin() -> None:
    # The note editor (Add Cards / Edit / Browse pane) — home of the flagship
    # tab-fill AI feature — shipped as pure stock Anki; the CFA skin must retone
    # it without touching the editor body/DOM.
    wc = SimpleNamespace(head="", body="<div class='fields'></div>")
    cfa_chrome.on_webview_will_set_content(wc, Editor())
    assert "cfa-chrome-editor" in wc.head
    # body left intact — the editor DOM is Anki's; only the skin is injected.
    assert wc.body == "<div class='fields'></div>"


def test_editor_retones_labels_and_focus_to_cfa() -> None:
    # Field labels become quiet CFA section labels and a focused field glows the
    # CFA accent instead of the stock-blue --border-focus ring.
    css = cfa_chrome._editor_css()
    accent = cfa_style.TOKENS["accent"]
    line = cfa_style.TOKENS["line"]
    assert ".label-name" in css
    assert "text-transform: uppercase;" in css
    assert ".editor-field:focus-within" in css
    assert f"outline-color: {accent} !important;" in css
    assert f"border-color: {line} !important;" in css
    # page tint, not a bare canvas
    assert cfa_style.TOKENS["primary_soft"] in css


def test_reviewer_gets_cfa_skin() -> None:
    # The MAIN reviewer webview (context Reviewer — the frame around every card)
    # shipped as pure stock Anki; the CFA skin must retone it without touching
    # the #qa card content (the notetype CSS / ethics templates own that).
    wc = SimpleNamespace(head="", body='<div id="qa" dir="auto"></div>')
    cfa_chrome.on_webview_will_set_content(wc, Reviewer())
    assert "cfa-chrome-reviewer" in wc.head
    assert wc.body == '<div id="qa" dir="auto"></div>'  # card content untouched


def test_reviewer_retones_page_tint_and_type_answer_feedback() -> None:
    # The study page sits on the CFA tint (light mode only, so night mode keeps
    # its dark canvas), and the type-in-answer diff uses the CFA pass/fail/
    # neutral washes instead of the stock #afa / #faa / #ccc traffic-light blocks.
    css = cfa_chrome._reviewer_css()
    t = cfa_style.TOKENS
    assert (
        f"body:not(.nightMode) {{\n    background: {t['primary_soft']} !important;"
        in css
    )
    assert f".typeGood {{\n    background: {t['pass_soft']} !important;" in css
    assert f".typeBad {{\n    background: {t['fail_soft']} !important;" in css
    assert ".typeMissed" in css
    # the harsh stock traffic-light colours are gone
    assert "#afa" not in css
    assert "#faa" not in css
    assert "#ccc" not in css


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
