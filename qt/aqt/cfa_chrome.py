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

import aqt
from aqt import gui_hooks


def _t() -> dict[str, str]:
    from aqt import cfa_style

    return cfa_style.TOKENS


def _toolbar_css() -> str:
    t = _t()
    # Re-skin the top bar as the same liquid-glass app bar used by the new CFA
    # pages: pearl glass, turquoise active/hover state, no stock Anki blue.
    # Sync (#sync / #sync-spinner) keeps its structure — only its colour changes.
    return f"""
<style id="cfa-chrome-toolbar">
  .header {{
    background: rgba(255, 255, 255, .70) !important;
    border-bottom: 1px solid rgba(255, 255, 255, .72);
    box-shadow: 0 14px 50px rgba(5, 59, 69, .10);
    backdrop-filter: blur(22px) saturate(1.25);
    -webkit-backdrop-filter: blur(22px) saturate(1.25);
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
  /* In native review mode Anki flattens the toolbar over the reviewer. Keep it
     visible for reviewer shortcuts/chrome, but make it read as a deliberate CFA
     review rail instead of an unrelated stock strip. */
  body.flat .header {{
    position: relative;
    background: rgba(255, 255, 255, .72) !important;
    border-bottom: 1px solid rgba(255, 255, 255, .72);
    box-shadow: 0 14px 50px rgba(5, 59, 69, .10);
  }}
  body.flat .header::before {{
    content: "CFA review mode";
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: {t["accent"]};
    font-size: {t["fs_eyebrow"]}px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    white-space: nowrap;
  }}
  @media (max-width: 640px) {{
    body.flat .header {{
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }}
    body.flat .header::before {{
      display: none;
    }}
    body.flat .hitem {{
      font-size: .82rem;
      padding-inline: 10px;
    }}
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
  @media (max-width: 640px) {{
    body {{
      overflow-x: hidden;
      padding-inline: 12px;
    }}
    .cfa-deck-banner,
    .cfa-deck-caption {{
      padding-inline: 0;
    }}
    .cfa-deck-banner {{
      margin-top: 16px;
    }}
    .cfa-deck-banner .title {{
      font-size: 28px;
      line-height: 1.08;
    }}
    a.deck {{
      min-height: 44px;
      display: inline-flex;
      align-items: center;
    }}
    table {{
      max-width: 100%;
    }}
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
  @media (max-width: 640px) {{
    body {{
      overflow-x: hidden;
      padding-inline: 12px;
    }}
    h3 {{
      font-size: 34px;
      line-height: 1.08;
    }}
    #study {{
      width: 100%;
      min-height: 48px;
      box-sizing: border-box;
      padding: 12px 18px;
    }}
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
    background: {t["primary_soft"]} !important;
    color: {t["ink"]};
    font-family: {t["font"]};
  }}
  #outer {{
    border-top: 1px solid {t["line"]} !important;
    background: rgba(255, 255, 255, .94);
    box-shadow: 0 -12px 30px rgba(18, 43, 70, .06);
    padding: 6px 14px 8px;
  }}
  #innertable {{
    max-width: 980px;
    margin: 0 auto;
  }}
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
  @media (max-width: 640px) {{
    #outer {{
      padding: 8px 8px calc(10px + env(safe-area-inset-bottom, 0px));
    }}
    #innertable,
    #innertable > tbody,
    #innertable > tbody > tr {{
      display: block;
      width: 100%;
    }}
    #innertable > tbody > tr {{
      display: grid;
      grid-template-columns: minmax(62px, .72fr) minmax(0, 2fr) minmax(62px, .72fr);
      align-items: end;
      gap: 6px;
    }}
    #middle {{
      min-width: 0;
    }}
    #middle > center,
    #middle > table,
    #middle table {{
      width: 100%;
    }}
    #middle table,
    #middle tbody,
    #middle tr {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 6px;
    }}
    #middle td[align=center] {{
      flex: 1 1 calc(50% - 6px);
      min-width: 0;
      padding-top: 14px !important;
    }}
    #middle button,
    #ansbut {{
      width: 100%;
      min-height: 46px;
      margin: 0;
      padding: 9px 10px;
      box-sizing: border-box;
    }}
    #ansbut {{
      min-height: 50px;
    }}
    #ansbut .stattxt {{
      width: max-content;
      max-width: 72vw;
    }}
    .stat {{
      display: block !important;
      padding-top: 4px;
    }}
    .stat button {{
      width: 100%;
      min-width: 0;
      min-height: 42px;
      margin: 0;
      padding: 8px 6px;
      font-size: .78rem;
    }}
    .nobold,
    .stattxt {{
      font-size: .68rem;
    }}
  }}
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
  @media (max-width: 640px) {{
    body {{
      overflow-x: hidden;
    }}
    .label-name {{
      font-size: 12px;
    }}
    .editor-field {{
      max-width: 100%;
    }}
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
  html, body {{
    min-height: 100%;
  }}
  body:not(.nightMode) {{
    background:
      radial-gradient(circle at 12% 0%, rgba(255,255,255,.96), transparent 23rem),
      radial-gradient(circle at 86% 8%, rgba(20,184,177,.22), transparent 28rem),
      radial-gradient(circle at 56% 70%, rgba(5,59,69,.16), transparent 34rem),
      linear-gradient(135deg, {t["bg"]} 0%, #EEF9F7 42%, #D8F3EF 64%, rgba(5,59,69,.24) 100%) !important;
    color: {t["ink"]};
    font-family: {t["font"]};
  }}
  body:not(.nightMode)::before {{
    content: "EthosPrep · Review mode";
    display: block;
    box-sizing: border-box;
    width: min(1040px, calc(100vw - 48px));
    margin: 22px auto -10px;
    padding: 0 4px;
    color: {t["accent"]};
    font-family: {t["font"]};
    font-size: {t["fs_eyebrow"]}px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
  }}
  body:not(.nightMode) #qa {{
    box-sizing: border-box;
    width: min(1040px, calc(100vw - 48px));
    min-height: min(58vh, 520px);
    margin: 26px auto 22px;
    padding: clamp(12px, 3vw, 28px);
    background: transparent;
    border: 0;
    border-radius: 0;
    box-shadow: none;
    text-align: left;
  }}
  body.nightMode #qa {{
    box-sizing: border-box;
    width: min(1040px, calc(100vw - 48px));
    margin: 26px auto 22px;
    padding: clamp(28px, 5vw, 54px);
    border: 1px solid #2b323b;
    border-radius: 28px;
  }}
  #qa .cfa-basic-review-card {{
    max-width: 860px;
    margin: 0 auto;
    padding: clamp(30px, 5vw, 46px);
    background: linear-gradient(135deg, rgba(255,255,255,.84), rgba(255,255,255,.50));
    border: 1px solid rgba(255,255,255,.72);
    border-radius: 34px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.78), 0 28px 90px rgba(5,59,69,.16);
    backdrop-filter: blur(22px) saturate(1.18);
    -webkit-backdrop-filter: blur(22px) saturate(1.18);
    color: {t["ink"]};
    line-height: 1.62;
  }}
  .nightMode #qa .cfa-basic-review-card {{
    color: #e8ecf1;
  }}
  #qa .cfa-basic-review-eyebrow {{
    font-family: {t["font"]};
    font-size: {t["fs_eyebrow"]}px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: {t["accent"]};
    margin-bottom: 16px;
  }}
  #qa .cfa-basic-review-content {{
    font-family: {t["font_heading"]};
    font-size: 1.38rem;
    line-height: 1.34;
    color: {t["ink"]};
  }}
  .nightMode #qa .cfa-basic-review-content {{
    color: #f2f5f8;
  }}
  #qa .cfa-basic-review-card--answer .cfa-basic-review-content {{
    font-family: {t["font"]};
    font-size: 1.02rem;
    line-height: 1.68;
  }}
  #qa .cfa-basic-review-card hr#answer,
  #qa .cfa-basic-review-card #answer {{
    border: none;
    border-top: 1px solid {t["line"]};
    margin: 22px 0;
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
  @media (max-width: 640px) {{
    body:not(.nightMode)::before {{
      width: calc(100vw - 24px);
      margin: 12px auto -8px;
      padding: 0;
    }}
    body:not(.nightMode) #qa,
    body.nightMode #qa {{
      width: calc(100vw - 16px);
      min-height: auto;
      margin: 14px auto 12px;
      padding: 8px;
    }}
    #qa .cfa-basic-review-card {{
      padding: 22px 18px;
      border-radius: 24px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.78), 0 18px 54px rgba(5,59,69,.16);
    }}
    #qa .cfa-basic-review-eyebrow {{
      margin-bottom: 12px;
    }}
    #qa .cfa-basic-review-content {{
      font-size: 1.18rem;
      line-height: 1.38;
    }}
    #qa .cfa-basic-review-card--answer .cfa-basic-review-content {{
      font-size: .98rem;
      line-height: 1.62;
    }}
  }}
</style>"""


def _card_deck_name(card: Any) -> str:
    try:
        deck_id = card.current_deck_id()
    except Exception:
        return ""
    try:
        col = getattr(aqt.mw, "col", None)
        if col is None:
            return ""
        return col.decks.name_if_exists(deck_id) or col.decks.name(deck_id)
    except Exception:
        return ""


def _is_cfa_deck_name(deck_name: str) -> bool:
    lower = deck_name.lower()
    if "cfa" in lower:
        return True
    return any(fragment in lower for fragment in _cfa_study_deck_name_fragments())


def _cfa_study_deck_name_fragments() -> tuple[str, ...]:
    """Deck names the CFA Study page can surface even without a CFA prefix."""
    try:
        from anki import cfa

        topics = [cfa.topic_display_name(topic) for topic in cfa.CANONICAL_TOPICS]
    except Exception:
        topics = []
    aliases = (
        "financial statement analysis",
        "financial reporting & analysis",
        "fra",
        "equity valuation",
        "equity investments",
        "ethics standards",
        "ethics & professional standards",
        "quant methods",
        "quantitative methods",
    )
    return tuple({*(topic.lower() for topic in topics), *aliases})


def _is_cfa_study_review_active() -> bool:
    try:
        return bool(getattr(aqt.mw, "_cfa_review_from_study", False))
    except Exception:
        return False


def _already_cfa_card(html: str) -> bool:
    return any(
        marker in html
        for marker in (
            "cfa-card",
            "cfa-basic-review-card",
            "cfa-ethics",
            "cfa-passage",
        )
    )


def _should_wrap_cfa_review_card(card: Any) -> bool:
    return _is_cfa_study_review_active() or _is_cfa_deck_name(_card_deck_name(card))


def _wrap_unbranded_cfa_card(html: str, kind: str) -> str:
    phase = "Answer" if kind.endswith("Answer") else "Question"
    modifier = phase.lower()
    return (
        f'<div class="cfa-basic-review-card cfa-basic-review-card--{modifier}">'
        '<div class="cfa-basic-review-eyebrow">'
        f"EthosPrep · Level II · {phase}"
        "</div>"
        f'<div class="cfa-basic-review-content">{html}</div>'
        "</div>"
    )


def _wrap_basic_cfa_card(html: str, kind: str) -> str:
    """Compatibility wrapper for proof tooling/tests that used the old name."""
    return _wrap_unbranded_cfa_card(html, kind)


def on_card_will_show(html: str, card: Any, kind: str) -> str:
    """Wrap unbranded cards on the live CFA review path with a CFA frame."""
    if not kind.startswith("review") or _already_cfa_card(html):
        return html
    if not _should_wrap_cfa_review_card(card):
        return html
    return _wrap_unbranded_cfa_card(html, kind)


def _deckbrowser_banner() -> str:
    return (
        '<div class="cfa-deck-banner">'
        '<div class="eyebrow">EthosPrep · Level II</div>'
        '<div class="title">Your decks</div>'
        "</div>"
    )


def _overview_eyebrow() -> str:
    # A quiet centred brand eyebrow above the deck title, so the study-intro
    # reads unmistakably as an EthosPrep screen (the deck name is the hero below).
    t = _t()
    return (
        '<div class="cfa-overview-eyebrow" style="text-align:center;'
        "font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
        f'margin-top:18px;font-size:{t["fs_eyebrow"]}px;color:{t["accent"]}">'
        "EthosPrep · Level II · Study session</div>"
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
    gui_hooks.card_will_show.append(on_card_will_show)
    gui_hooks.deck_browser_will_render_content.append(
        on_deck_browser_will_render_content
    )
    _registered = True
