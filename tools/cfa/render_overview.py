#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render the CFA-skinned deck study-intro (Overview) to a standalone HTML.

Phase-B Pass-4 desktop. The Overview is the screen you land on when you pick a
deck or click Study — a stock Anki ``Overview`` webview that shipped un-themed
(plain sans deck title, a stock-blue "New" count, and a stock-blue primary
"Study Now" button). ``aqt.cfa_chrome`` now re-skins it additively (page tint +
serif deck title + navy "Study Now" CTA + a brand eyebrow).

This tool reproduces the EXACT surface the Qt webview renders — the compiled
base ``overview.css`` (root-vars + count colours + the ``#study`` button rules)
followed by the live ``cfa_chrome._overview_css()`` and ``_overview_eyebrow()``,
over the real Overview body template — so the before/after screenshots reflect
the real cascade (specificity, ``!important``, everything).

Usage:
    python3 tools/cfa/render_overview.py OUT.html [--stock]

``--stock`` omits the CFA chrome, producing the stock-Anki "before" surface.
Then screenshot the file with chrome-devtools-axi. No Anki launch needed.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))

_BASE_CSS = os.path.join(
    _ROOT, "out", "qt", "_aqt", "data", "web", "css", "overview.css"
)


def _base_css() -> str:
    with open(_BASE_CSS, encoding="utf-8") as fh:
        return fh.read()


def _overview_body() -> str:
    # Reproduce Overview._body / _table exactly: centred deck title, description,
    # the new/learn/review count table, and the autofocus "Study Now" button.
    return (
        "<center>"
        "<h3>CFA Level II · Ethics &amp; Professional Standards</h3>"
        '<div class="descfont descmid description">Standards of Practice — '
        "minimal-pair reasoning drills. Highlight the decisive evidence and "
        "judge the conduct.</div>"
        "<table width=400 cellpadding=5>"
        "<tr><td align=center valign=top>"
        "<table cellspacing=5>"
        "<tr><td>New:</td><td><b><span class=new-count>20</span></b></td></tr>"
        "<tr><td>Learning:</td><td><b><span class=learn-count>2</span></b></td></tr>"
        "<tr><td>To review:</td><td><b><span class=review-count>12</span></b></td></tr>"
        "</table>"
        "</td><td align=center>"
        '<button id="study" autofocus>Study Now</button>'
        "</td></tr></table>"
        "</center>"
    )


def build_html(stock: bool = False) -> str:
    from aqt import cfa_chrome

    chrome_css = "" if stock else cfa_chrome._overview_css()
    eyebrow = "" if stock else cfa_chrome._overview_eyebrow()
    body = eyebrow + _overview_body()
    return (
        "<!doctype html><html><head><meta charset=utf-8>"
        f"<style>{_base_css()}</style>{chrome_css}</head>"
        f"<body>{body}</body></html>"
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    stock = "--stock" in args
    positional = [a for a in args if not a.startswith("--")]
    out = positional[0] if positional else os.path.join(_HERE, "overview.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build_html(stock=stock))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
