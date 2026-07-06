#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render the CFA-skinned deck browser (D8) to a standalone HTML for capture.

Phase-B Pass-2 desktop. The deck list is a stock Anki ``DeckBrowser`` webview
that ``aqt.cfa_chrome`` re-skins additively (page tint + brand banner + CFA
type/link colours). This tool reproduces the EXACT surface the Qt webview
renders — the compiled base ``deckbrowser.css`` (root-vars + card-counts +
deck-table rules) followed by the live ``cfa_chrome._deckbrowser_css()`` and
``_deckbrowser_banner()`` — over a realistic CFA deck tree, so the before/after
screenshots reflect the real cascade (specificity, ``!important``, everything).

Usage:
    python3 tools/cfa/render_deck_browser.py OUT.html

Then screenshot the file with chrome-devtools-axi. No Anki launch needed.
"""

from __future__ import annotations

import html
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))

# The compiled base css the real webview loads (root-vars + card-counts +
# deckbrowser base rules), so the leaks (.new-count/.filtered stock blue) and
# the exact deck-table cascade are faithfully present.
_BASE_CSS = os.path.join(
    _ROOT, "out", "qt", "_aqt", "data", "web", "css", "deckbrowser.css"
)


def _base_css() -> str:
    with open(_BASE_CSS, encoding="utf-8") as fh:
        return fh.read()


def _deck_row(name: str, new: int, learn: int, review: int, *, filtered: bool) -> str:
    """Reproduce DeckBrowser._render_deck_node's exact markup + classes."""

    def cnt(n: int, klass: str) -> str:
        if not n:
            klass = "zero-count"
        return f'<span class="{klass}">{n}</span>'

    extra = "filtered" if filtered else ""
    collapse = "<span class=collapse></span>"
    return (
        "<tr class='deck' id='1'>"
        f"<td class=decktd colspan=5>{collapse}"
        f'<a class="deck {extra}" href=#>{html.escape(name)}</a></td>'
        f"<td align=end>{cnt(new, 'new-count')}</td>"
        f"<td align=end>{cnt(learn, 'learn-count')}</td>"
        f"<td align=end>{cnt(review, 'review-count')}</td>"
        "<td align=center class=opts><a><span class=gears>&#9881;</span></a></td>"
        "</tr>"
    )


def _deck_table() -> str:
    # A realistic CFA collection: a normal deck plus three curated filtered
    # study decks (the ones that leak stock blue on names + new counts).
    header = (
        "<tr><th colspan=5 align=start>Deck</th>"
        "<th class=count>New</th><th class=count>Learn</th>"
        "<th class=count>Review</th><th class=optscol></th></tr>"
        "<tr class='top-level-drag-row'><td colspan='6'>&nbsp;</td></tr>"
    )
    rows = [
        _deck_row("CFA Level II", 20, 0, 12, filtered=False),
        _deck_row("Ethics Pairs", 29, 0, 4, filtered=True),
        _deck_row("Study — Ethics Minimal-Pairs", 99, 2, 0, filtered=True),
        _deck_row("CFA Exam Priority", 1, 0, 8, filtered=True),
    ]
    return "<table cellspacing=0 cellpadding=3>" + header + "".join(rows) + "</table>"


def build_html() -> str:
    from aqt import cfa_chrome

    chrome_css = cfa_chrome._deckbrowser_css()
    banner = cfa_chrome._deckbrowser_banner()
    caption = (
        '<div class="cfa-deck-caption">CFA Level II · pick a deck, or use '
        "Home / Study / Ethics / Readiness on the top bar.</div>"
    )
    body = banner + _deck_table() + '<div id="studiedToday"></div>' + caption
    return (
        "<!doctype html><html><head><meta charset=utf-8>"
        f"<style>{_base_css()}</style>{chrome_css}</head>"
        f"<body>{body}</body></html>"
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    out = args[0] if args else os.path.join(_HERE, "deck_browser.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build_html())
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
