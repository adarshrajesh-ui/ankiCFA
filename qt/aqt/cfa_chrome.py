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


def _deckbrowser_banner() -> str:
    return (
        '<div class="cfa-deck-banner">'
        '<div class="eyebrow">ankiCFA · Level II</div>'
        '<div class="title">Your decks</div>'
        "</div>"
    )


def on_webview_will_set_content(web_content: Any, context: object | None) -> None:
    # Fires for every stdHtml webview; only re-skin the toolbar + deck list.
    name = type(context).__name__
    if name == "TopToolbar":
        web_content.head += _toolbar_css()
    elif name == "DeckBrowser":
        web_content.head += _deckbrowser_css()
        web_content.body = _deckbrowser_banner() + web_content.body


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
