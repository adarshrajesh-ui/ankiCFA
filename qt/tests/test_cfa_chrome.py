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
    # parity palette: turquoise glass accent from the locked TOKENS
    assert cfa_style.TOKENS["accent"].lower() in wc.head.lower()
    assert ".hitem" in wc.head
    # Review mode keeps native toolbar behavior, but it reads as a deliberate
    # CFA review rail when Anki flattens it over the reviewer.
    assert "body.flat .header" in wc.head
    assert 'content: "CFA review mode";' in wc.head


def test_toolbar_review_rail_has_phone_overflow_treatment() -> None:
    css = cfa_chrome._toolbar_css()
    assert "@media (max-width: 640px)" in css
    assert "body.flat .header" in css
    assert "-webkit-overflow-scrolling: touch;" in css
    assert "body.flat .header::before" in css
    assert "display: none;" in css


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


def test_reviewer_bottom_is_deliberate_cfa_bar() -> None:
    # The bottom reviewer controls remain Anki's real controls, but the bar
    # should no longer read as a plain stock footer.
    css = cfa_chrome._reviewer_bottom_css()
    assert f"background: {cfa_style.TOKENS['primary_soft']} !important;" in css
    assert "#innertable" in css
    assert "box-shadow: 0 -12px 30px rgba(18, 43, 70, .06);" in css


def test_reviewer_bottom_has_phone_layout_without_hiding_controls() -> None:
    # Stock Anki hides Edit/More on narrow reviewer bars. The CFA mobile review
    # chrome keeps those real controls reachable while wrapping the ease buttons.
    css = cfa_chrome._reviewer_bottom_css()
    assert "@media (max-width: 640px)" in css
    assert "#innertable > tbody > tr" in css
    assert (
        "grid-template-columns: minmax(62px, .72fr) minmax(0, 2fr) minmax(62px, .72fr);"
        in css
    )
    assert ".stat {" in css
    assert "display: block !important;" in css
    assert "min-height: 46px;" in css
    assert "env(safe-area-inset-bottom, 0px)" in css


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
    assert "radial-gradient(circle at 86% 8%, rgba(20,184,177,.22)" in css
    assert f"linear-gradient(135deg, {t['bg']} 0%" in css
    assert f".typeGood {{\n    background: {t['pass_soft']} !important;" in css
    assert f".typeBad {{\n    background: {t['fail_soft']} !important;" in css
    assert ".typeMissed" in css
    # the harsh stock traffic-light colours are gone
    assert "#afa" not in css
    assert "#faa" not in css
    assert "#ccc" not in css


def test_reviewer_frames_card_area_as_cfa_review_surface() -> None:
    # The screenshot regression was the card itself sitting in a huge plain stock
    # void. The reviewer body now provides the liquid-glass page and leaves the
    # actual card shell to CFA-branded notes / the Basic wrapper.
    css = cfa_chrome._reviewer_css()
    assert 'content: "EthosPrep · Review mode";' in css
    assert "body:not(.nightMode)::before" in css
    assert "body:not(.nightMode) #qa" in css
    assert "width: min(1040px, calc(100vw - 48px));" in css
    assert "background: transparent;" in css
    assert "box-shadow: none;" in css
    assert "border-radius: 34px;" in css
    assert "0 28px 90px rgba(5,59,69,.16)" in css


def test_reviewer_body_has_phone_card_frame() -> None:
    # On phone the Study -> reviewer body should use the same liquid-glass frame,
    # but tightened to the viewport instead of a desktop-width review canvas.
    css = cfa_chrome._reviewer_css()
    assert "@media (max-width: 640px)" in css
    assert "width: calc(100vw - 16px);" in css
    assert "margin: 14px auto 12px;" in css
    assert "#qa .cfa-basic-review-card" in css
    assert "border-radius: 24px;" in css
    assert "min-height: auto;" in css


def test_basic_cards_in_cfa_decks_are_wrapped_for_review(monkeypatch) -> None:
    # User-added Study cards can still be Basic notes. In CFA decks, the review
    # hook wraps only their rendered HTML with a CFA frame; scheduling/card data
    # is untouched.
    decks = SimpleNamespace(
        name_if_exists=lambda deck_id: "CFA Level II",
        name=lambda deck_id: "CFA Level II",
    )
    monkeypatch.setattr(
        cfa_chrome.aqt,
        "mw",
        SimpleNamespace(col=SimpleNamespace(decks=decks)),
        raising=False,
    )
    card = SimpleNamespace(
        current_deck_id=lambda: 42,
        note_type=lambda: {"name": "Basic"},
    )

    html = cfa_chrome.on_card_will_show(
        "Name the three factors in the Fama-French model.",
        card,
        "reviewQuestion",
    )

    assert "cfa-basic-review-card cfa-basic-review-card--question" in html
    assert "EthosPrep · Level II · Question" in html
    assert "Fama-French" in html


def test_basic_cards_in_cfa_study_topic_decks_are_wrapped(monkeypatch) -> None:
    # The Study page can surface CFA topic decks whose names do not literally
    # contain "CFA". Those Basic cards still need the EthosPrep review frame.
    decks = SimpleNamespace(
        name_if_exists=lambda deck_id: "Equity Investments",
        name=lambda deck_id: "Equity Investments",
    )
    monkeypatch.setattr(
        cfa_chrome.aqt,
        "mw",
        SimpleNamespace(col=SimpleNamespace(decks=decks)),
        raising=False,
    )
    card = SimpleNamespace(
        current_deck_id=lambda: 42,
        note_type=lambda: {"name": "Basic"},
    )

    html = cfa_chrome.on_card_will_show(
        "Explain residual income valuation.",
        card,
        "reviewQuestion",
    )

    assert "cfa-basic-review-card cfa-basic-review-card--question" in html
    assert "Explain residual income valuation." in html


def test_basic_cards_launched_from_cfa_study_are_wrapped(monkeypatch) -> None:
    # If Study falls back to an ordinary user deck, the live Study -> reviewer
    # route still marks that review session as an EthosPrep study surface.
    decks = SimpleNamespace(
        name_if_exists=lambda deck_id: "Default",
        name=lambda deck_id: "Default",
    )
    monkeypatch.setattr(
        cfa_chrome.aqt,
        "mw",
        SimpleNamespace(
            _cfa_review_from_study=True,
            col=SimpleNamespace(decks=decks),
        ),
        raising=False,
    )
    card = SimpleNamespace(
        current_deck_id=lambda: 1,
        note_type=lambda: {"name": "Basic"},
    )

    html = cfa_chrome.on_card_will_show("Plain Basic", card, "reviewQuestion")

    assert "cfa-basic-review-card cfa-basic-review-card--question" in html
    assert "Plain Basic" in html


def test_unbranded_cfa_knowledge_cards_launched_from_study_are_wrapped(
    monkeypatch,
) -> None:
    # Existing seeded profiles may already have CFA Knowledge notes whose
    # templates predate the branded .cfa-card markup. The live Study route should
    # still frame their rendered card body as an EthosPrep review surface.
    decks = SimpleNamespace(
        name_if_exists=lambda deck_id: "CFA Level II",
        name=lambda deck_id: "CFA Level II",
    )
    monkeypatch.setattr(
        cfa_chrome.aqt,
        "mw",
        SimpleNamespace(
            _cfa_review_from_study=True,
            col=SimpleNamespace(decks=decks),
        ),
        raising=False,
    )
    card = SimpleNamespace(
        current_deck_id=lambda: 42,
        note_type=lambda: {"name": "CFA Knowledge"},
    )

    html = cfa_chrome.on_card_will_show(
        "Name the three factors in the Fama-French model.",
        card,
        "reviewQuestion",
    )

    assert "cfa-basic-review-card cfa-basic-review-card--question" in html
    assert "Fama-French" in html


def test_card_wrapper_leaves_non_cfa_and_branded_cards_untouched(monkeypatch) -> None:
    decks = SimpleNamespace(
        name_if_exists=lambda deck_id: "Default",
        name=lambda deck_id: "Default",
    )
    monkeypatch.setattr(
        cfa_chrome.aqt,
        "mw",
        SimpleNamespace(col=SimpleNamespace(decks=decks)),
        raising=False,
    )
    card = SimpleNamespace(
        current_deck_id=lambda: 1,
        note_type=lambda: {"name": "Basic"},
    )

    assert cfa_chrome.on_card_will_show("Plain", card, "reviewQuestion") == "Plain"
    assert (
        cfa_chrome.on_card_will_show(
            '<div class="cfa-card">Branded</div>', card, "reviewQuestion"
        )
        == '<div class="cfa-card">Branded</div>'
    )


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
    before_web = len(gui_hooks.webview_will_set_content._hooks)
    before_card = len(gui_hooks.card_will_show._hooks)
    cfa_chrome.register()
    cfa_chrome.register()
    after_web = len(gui_hooks.webview_will_set_content._hooks)
    after_card = len(gui_hooks.card_will_show._hooks)
    assert after_web == before_web + 1  # registered exactly once despite two calls
    assert after_card == before_card + 1
