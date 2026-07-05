# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA chrome — apply the CFA design system to the shared Anki web surfaces.

The CFA Home dashboard, Readiness and Deadline pages are already CFA-native
(SvelteKit + the design system). This module additively re-skins the *remaining*
stock surfaces — the top toolbar and the deck list — so no screen reads as
plain Anki:

* the top toolbar (``TopToolbar`` webview): CFA palette + type, orange hover,
* the deck list (``DeckBrowser`` webview): CFA page tint + type + a quiet brand
  banner, and a CFA caption via ``deck_browser_will_render_content``.
* the deck study-intro (``Overview`` webview): CFA page tint + serif deck title
  + a navy "Study Now" primary CTA (was stock-blue) + a brand eyebrow.
* the reviewer answer bar (``ReviewerBottomBar`` webview): CFA-styled rating
  chips, a navy "Show Answer" primary pill, a quiet caution border on "Again",
  and a filled-navy recommended (default) answer — so the most-used study
  surface no longer shows stock-Anki native buttons.
* the note editor (``Editor`` webview — Add Cards / Edit / the Browse pane):
  CFA page tint + quiet CFA field labels + a warm-accent focus ring, so the
  surface that hosts the flagship "Tab to complete the back" AI feature reads
  as a CFA screen rather than stock Anki.
* the main reviewer body (``Reviewer`` webview — the frame around every card):
  CFA page tint (light mode) + CFA pass/fail/neutral type-answer feedback
  washes replacing the stock #afa/#faa/#ccc traffic-light blocks, so the
  highest-time-on-screen surface reads as CFA even for cards that don't paint
  their own background.

Palette/type come from :data:`aqt.cfa_style.TOKENS` (parity-locked to the web
``_tokens.scss``), so the chrome matches the SvelteKit pages exactly. Everything
is registered through public ``gui_hooks`` — no stock render code is rewritten.
"""

from __future__ import annotations

from typing import Any

from aqt import gui_hooks


def _t() -> dict[str, str]:
    from aqt import cfa_style

    return cfa_style.TOKENS


def _toolbar_css() -> str:
    t = _t()
    # Re-skin the top bar: calm CFA surface, navy-muted links, warm accent hover.
    # Sync (#sync / #sync-spinner) keeps its structure — only its colour changes.
    return f"""
<style id="cfa-chrome-toolbar">
  .header {{
    background: {t["bg"]} !important;
    border-bottom: 1px solid {t["line"]};
    font-family: {t["font"]};
  }}
  .hitem {{
    color: {t["muted"]} !important;
    font-weight: 600;
    letter-spacing: .01em;
    border-radius: 100px;
  }}
  .hitem:hover {{
    color: {t["accent"]} !important;
    background: {t["accent_soft"]};
  }}
  /* Active-tab "you are here" marker. Stock Anki's toolbar has no active-tab
     concept, so the CFA nav (Home / Concept Map / Readiness) read as an
     undifferentiated row of links — a product nav should always show which
     section you're in. The current tab is a filled accent pill (white text on
     the warm accent), a clear selected-segment treatment that reads instantly
     and stays put on hover. Applied via `is-active` + `aria-current="page"`
     from Toolbar._update_active_cfa_tab. */
  .hitem.is-active,
  .hitem.is-active:hover {{
    color: {t["bg"]} !important;
    background: {t["accent"]};
  }}
  /* The single context-aware sync-account control (Connect / Log out) reads as
     a distinct bordered chip, set apart from the plain nav links so account
     management is discoverable without crowding the bar with extra links. */
  #cfa_account {{
    border: 1px solid {t["line"]};
    color: {t["ink"]} !important;
    margin-left: 6px;
  }}
  #cfa_account:hover {{
    border-color: {t["accent"]};
    color: {t["accent"]} !important;
    background: {t["accent_soft"]};
  }}
</style>"""


def _deckbrowser_css() -> str:
    t = _t()
    # Tint the deck list to the CFA page, set the brand type + link colours, and
    # calm the table rules — without fighting Anki's exact deck-row classes.
    return f"""
<style id="cfa-chrome-deckbrowser">
  html, body {{
    background: {t["primary_soft"]} !important;
    color: {t["ink"]};
    font-family: {t["font"]};
  }}
  a {{ color: {t["ink"]}; }}
  a:hover {{ color: {t["accent"]}; }}
  table tr {{ border-color: {t["line"]}; }}
  .gears {{ opacity: .55; }}
  .gears:hover {{ opacity: 1; }}
  /* Stock Anki paints the deck list with its own blue: filtered/dynamic deck
     NAMES use --fg-link and the "New" COUNT uses --state-new, both of which
     leaked through the navy CFA shell (parity with the mobile M6-1 fix). The
     CFA study decks are curated study modes, not an Anki internal to surface
     in loud blue — retone both to brand navy so the deck list reads as one
     cohesive CFA product. Learn (red) / Review (green) keep their learned
     Anki count semantics; the orange top-bar accent stays the single warm
     accent. `a.deck`/`a.deck.filtered` match Anki's own specificity + the
     `.filtered !important`, so this wins the cascade without a token change. */
  a.deck {{ color: {t["ink"]} !important; }}
  a.deck.filtered {{ color: {t["ink"]} !important; }}
  .new-count {{ color: {t["ink"]} !important; }}
  .cfa-deck-banner {{
    max-width: 820px;
    margin: 22px auto 8px;
    padding: 0 8px;
    text-align: left;
    font-family: {t["font"]};
  }}
  .cfa-deck-banner .eyebrow {{
    font-size: {t["fs_eyebrow"]}px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: {t["accent"]};
  }}
  .cfa-deck-banner .title {{
    font-family: {t["font_heading"]};
    font-size: {t["fs_title"]}px;
    font-weight: 600;
    color: {t["ink"]};
    margin-top: 2px;
  }}
  .cfa-deck-caption {{
    max-width: 820px;
    margin: 10px auto 0;
    padding: 0 8px;
    font-size: {t["fs_meta"]}px;
    color: {t["faint"]};
    text-align: left;
  }}
</style>"""


def _overview_css() -> str:
    t = _t()
    # The deck study-intro (Overview) is the screen you land on when you pick a
    # deck or click Study — and it shipped as pure stock Anki: a plain sans deck
    # title, a stock-blue "New" count, and a stock-blue primary "Study Now"
    # button (`--button-primary-bg`). Retone it to the CFA design system so the
    # study-intro reads as a purpose-built CFA screen, not plain Anki.
    return f"""
<style id="cfa-chrome-overview">
  html, body {{
    background: {t["primary_soft"]} !important;
    color: {t["ink"]};
    font-family: {t["font"]};
  }}
  h3 {{
    font-family: {t["font_heading"]};
    font-size: {t["fs_hero"]}px;
    font-weight: 600;
    color: {t["ink"]};
  }}
  .descfont, .description {{ color: {t["muted"]} !important; }}
  a {{ color: {t["ink"]}; }}
  a:hover {{ color: {t["accent"]}; }}
  /* Retone the stock-blue "New" count to brand navy (parity with the deck-list
     D8-1 fix); the learned Learn=red / Review=green count semantics are left
     untouched. */
  .new-count {{ color: {t["ink"]} !important; }}
  /* The single primary CTA on this screen — "Study Now" — was stock Anki blue
     (`--button-primary-bg`). Retone it to the brand navy pill so the study-intro
     matches the rest of the CFA product, mirroring the mobile reviewer
     "Show answer" navy decision (M8-1). */
  #study {{
    background: {t["primary"]} !important;
    color: {t["bg"]} !important;
    border: none;
    border-radius: 100px;
    padding: 10px 28px;
    font-weight: 600;
    font-family: {t["font"]};
  }}
  #study:hover {{
    background: {t["primary_hover"]} !important;
  }}
</style>"""


def _reviewer_bottom_css() -> str:
    t = _t()
    # The reviewer answer bar (Show Answer + Again/Hard/Good/Easy) is THE
    # most-used study surface, and it shipped as pure stock Anki: native gray
    # <button> elements on a plain bar. Retone it to the CFA design system so
    # studying reads as a purpose-built CFA product:
    #   * the bar sits on the calm CFA page with a hairline top rule,
    #   * "Edit"/"More" become quiet text buttons (accent on hover),
    #   * rating buttons become rounded CFA chips (hairline → accent-soft hover),
    #   * "Show Answer" (#ansbut) is the single navy primary pill CTA,
    #   * the recommended/default answer (#defease) is a filled navy pill so the
    #     eye is guided to it, mirroring the desktop/mobile primary decision,
    #   * "Again" (data-ease=1 is always Again, regardless of button count)
    #     carries a quiet fail-red caution border — the one unambiguous rating
    #     cue worth keeping; the other tiers stay neutral to avoid the
    #     stock-addon traffic-light look and the Good/Hard ambiguity that a
    #     count-varying data-ease number would introduce.
    return f"""
<style id="cfa-chrome-reviewer-bottom">
  html, body {{
    background: {t["bg"]} !important;
    color: {t["ink"]};
    font-family: {t["font"]};
  }}
  #outer {{ border-top: 1px solid {t["line"]} !important; }}
  /* Edit / More — quiet text buttons, not native gray chrome. */
  .stat button {{
    background: transparent !important;
    border: none !important;
    color: {t["muted"]} !important;
    font-family: {t["font"]};
    font-weight: 600;
  }}
  .stat button:hover {{ color: {t["accent"]} !important; }}
  /* Rating chips + Show Answer — one rounded CFA pill shape. */
  #middle button, #ansbut {{
    font-family: {t["font"]};
    font-weight: 600;
    border-radius: 100px;
    border: 1px solid {t["line"]};
    background: {t["bg"]};
    color: {t["ink"]};
    padding: 8px 20px;
  }}
  #middle button:hover {{
    border-color: {t["accent"]};
    color: {t["accent"]};
    background: {t["accent_soft"]};
  }}
  /* Show Answer — the single navy primary pill CTA. */
  #ansbut, #ansbut:hover {{
    background: {t["primary"]} !important;
    color: {t["bg"]} !important;
    border-color: {t["primary"]} !important;
  }}
  #ansbut:hover {{ background: {t["primary_hover"]} !important; }}
  /* Recommended/default answer — filled navy pill so the eye is guided. */
  #defease, #defease:hover {{
    background: {t["primary"]} !important;
    color: {t["bg"]} !important;
    border-color: {t["primary"]} !important;
  }}
  #defease:hover {{ background: {t["primary_hover"]} !important; }}
  /* "Again" (ease 1) — a quiet caution border, unless it is the default. */
  #middle button[data-ease="1"]:not(#defease) {{
    border-color: {t["fail"]};
    color: {t["fail"]};
  }}
  #middle button[data-ease="1"]:not(#defease):hover {{
    border-color: {t["fail"]};
    color: {t["fail"]};
    background: {t["fail_soft"]};
  }}
  /* Interval labels + remaining-count stay quiet. */
  .nobold, .stattxt {{ color: {t["faint"]}; }}
  .new-count {{ color: {t["ink"]}; }}
</style>"""


def _editor_css() -> str:
    t = _t()
    # The note editor (Add Cards / Edit Current / the Browse editor pane) is the
    # surface that hosts the flagship "Tab to complete the back" AI feature — yet
    # it shipped as pure stock Anki: field cards on a bare `--canvas`, plain sans
    # field labels, and a stock-blue focus ring. Retone it to the CFA design
    # system so the editor reads as a purpose-built CFA screen:
    #   * the editor sits on the calm CFA page tint (white field cards on top),
    #   * field labels become quiet CFA section labels (navy-muted, tracked caps),
    #   * field cards get a hairline CFA border,
    #   * a focused field glows the warm CFA accent instead of stock blue.
    # Presentation-only, and it leaves the rich-text content, toolbar icons and
    # the tab-fill affordance (which already uses the accent) untouched.
    return f"""
<style id="cfa-chrome-editor">
  html, body {{
    background: {t["primary_soft"]} !important;
    font-family: {t["font"]};
    color: {t["ink"]};
  }}
  /* Field labels read as quiet CFA section labels, not plain sans text. */
  .label-name {{
    font-family: {t["font"]};
    color: {t["muted"]} !important;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    font-size: {t["fs_meta"]}px;
  }}
  /* Field cards keep a white face (editing legibility) with a hairline CFA
     border instead of the stock grey. */
  .editor-field {{
    border-color: {t["line"]} !important;
  }}
  /* A focused field glows the warm CFA accent (was the stock-blue
     `--border-focus` ring), matching the accent used by every other CFA
     control and the tab-fill affordance. */
  .editor-field:focus-within {{
    outline-color: {t["accent"]} !important;
  }}
</style>"""


def _reviewer_css() -> str:
    t = _t()
    # The MAIN reviewer webview (context ``Reviewer`` — the frame around every
    # card during Study) shipped as pure stock Anki: a plain white body void and
    # stock traffic-light type-answer feedback (#afa / #faa / #ccc). The card
    # CONTENT is CFA-branded (the "CFA Knowledge" notetype CSS + the ethics
    # templates), but the surface AROUND it was not. Retone it so the highest-
    # time-on-screen surface reads as a purpose-built CFA product:
    #   * the study page sits on the same calm CFA tint as Overview / Editor
    #     (light mode only — night mode keeps its dark --canvas), so a card that
    #     doesn't paint its own background isn't a bare-white rectangle,
    #   * the type-in-answer diff (typeGood / typeBad / typeMissed) uses the CFA
    #     pass / fail / neutral washes instead of the harsh stock #afa/#faa/#ccc,
    #     with brand-ink text for legibility.
    # Presentation-only and additive: it never touches #qa card content, so the
    # notetype CSS and ethics templates stay authoritative on the card itself.
    return f"""
<style id="cfa-chrome-reviewer">
  body:not(.nightMode) {{
    background: {t["primary_soft"]} !important;
  }}
  /* Type-in-answer diff — CFA pass / fail / neutral washes, brand-ink text,
     replacing the stock bright-green / bright-red / grey traffic-light blocks. */
  .typeGood {{
    background: {t["pass_soft"]} !important;
    color: {t["ink"]} !important;
  }}
  .typeBad {{
    background: {t["fail_soft"]} !important;
    color: {t["ink"]} !important;
  }}
  .typeMissed {{
    background: {t["line"]} !important;
    color: {t["muted"]} !important;
  }}
</style>"""


def _deckbrowser_banner() -> str:
    return (
        '<div class="cfa-deck-banner">'
        '<div class="eyebrow">ankiCFA · Level II</div>'
        '<div class="title">Your decks</div>'
        "</div>"
    )


def _overview_eyebrow() -> str:
    # A quiet centred brand eyebrow above the deck title, so the study-intro
    # reads unmistakably as an ankiCFA screen (the deck name is the hero below).
    t = _t()
    return (
        '<div class="cfa-overview-eyebrow" style="text-align:center;'
        "font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
        f'margin-top:18px;font-size:{t["fs_eyebrow"]}px;color:{t["accent"]}">'
        "ankiCFA · Level II · Study session</div>"
    )


def on_webview_will_set_content(web_content: Any, context: object | None) -> None:
    # Fires for every stdHtml webview; only re-skin the toolbar + deck list +
    # the deck study-intro (Overview).
    name = type(context).__name__
    if name == "TopToolbar":
        web_content.head += _toolbar_css()
    elif name == "DeckBrowser":
        web_content.head += _deckbrowser_css()
        web_content.body = _deckbrowser_banner() + web_content.body
    elif name == "Overview":
        web_content.head += _overview_css()
        web_content.body = _overview_eyebrow() + web_content.body
    elif name == "ReviewerBottomBar":
        web_content.head += _reviewer_bottom_css()
    elif name == "Editor":
        web_content.head += _editor_css()
    elif name == "Reviewer":
        web_content.head += _reviewer_css()


def on_deck_browser_will_render_content(deck_browser: Any, content: Any) -> None:
    # Quiet CFA footnote under the deck list (Home is one click away on the top bar).
    content.stats += (
        '<div class="cfa-deck-caption">CFA Level II · pick a deck, or use '
        "Home / Study / Ethics / Readiness on the top bar.</div>"
    )


_registered = False


def register() -> None:
    """Install the CFA chrome hooks once (idempotent)."""
    global _registered
    if _registered:
        return
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    gui_hooks.deck_browser_will_render_content.append(
        on_deck_browser_will_render_content
    )
    _registered = True
