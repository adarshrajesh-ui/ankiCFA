#!/usr/bin/env python3
"""Render the CFA-skinned reviewer answer bar to a standalone HTML.

Phase-B Pass-4 desktop. The reviewer bottom bar (Show Answer + the
Again/Hard/Good/Easy rating buttons) is THE most-used study surface, and it
shipped as pure stock Anki: native gray ``<button>`` elements on a plain bar.
``aqt.cfa_chrome`` now re-skins it additively (rounded CFA rating chips, a navy
"Show Answer" primary pill, a filled-navy recommended answer, and a quiet
fail-red caution border on "Again").

This tool reproduces the EXACT surface the Qt bottom webview renders — the
compiled base ``toolbar-bottom.css`` + ``reviewer-bottom.css`` followed by the
live ``cfa_chrome._reviewer_bottom_css()`` — over the real answer-bar body
(``Reviewer._bottomHTML`` + ``_answerButtons``), so the before/after
screenshots reflect the real cascade. No Anki launch needed.

Usage:
    python3 tools/cfa/render_reviewer_bottom.py OUT.html [--stock] [--question]

``--stock`` omits the CFA chrome (the stock-Anki "before"). ``--question``
renders the Show-Answer phase instead of the ease-button phase.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_CSS_DIR = os.path.join(_ROOT, "out", "qt", "_aqt", "data", "web", "css")


def _base_css() -> str:
    parts = []
    for name in ("toolbar-bottom.css", "reviewer-bottom.css"):
        with open(os.path.join(_CSS_DIR, name), encoding="utf-8") as fh:
            parts.append(fh.read())
    return "\n".join(parts)


def _ease_middle() -> str:
    # Reproduce Reviewer._answerButtons: a 4-ease row with data-ease + the
    # default-ease id="defease" on Good (3), plus the interval labels (.nobold).
    def but(ease: int, label: str, interval: str, default: bool = False) -> str:
        extra = 'id="defease" ' if default else ""
        return (
            f'<td align=center><button {extra}data-ease="{ease}" '
            f"onclick='pycmd(\"ease{ease}\");'>{label}"
            f'<span class="nobold">{interval}</span></button></td>'
        )

    return (
        "<center><table cellpadding=0 cellspacing=0><tr>"
        + but(1, "Again", "&lt;1m")
        + but(2, "Hard", "8m")
        + but(3, "Good", "1d", default=True)
        + but(4, "Easy", "4d")
        + "</tr></table></center>"
    )


def _show_answer_middle() -> str:
    return (
        "<table cellpadding=0><tr><td class=stat2 align=center>"
        '<button id="ansbut" onclick=\'pycmd("ans");\'>Show Answer'
        "<span class=stattxt>"
        "<span class=new-count>20</span> + "
        "<span class=learn-count>2</span> + "
        "<span class=review-count>12</span></span></button>"
        "</td></tr></table>"
    )


def _bottom_body(question: bool = False) -> str:
    middle = _show_answer_middle() if question else _ease_middle()
    return (
        "<center id=outer>"
        "<table id=innertable width=100% cellspacing=0 cellpadding=0><tr>"
        "<td align=start valign=top class=stat>"
        "<button onclick=\"pycmd('edit');\">Edit</button></td>"
        f"<td align=center valign=top id=middle>{middle}</td>"
        "<td align=end valign=top class=stat>"
        "<button onclick=\"pycmd('more');\">More &#9662;"
        "<span id=time class=stattxt></span></button></td>"
        "</tr></table></center>"
    )


def build_html(stock: bool = False, question: bool = False) -> str:
    from aqt import cfa_chrome

    chrome_css = "" if stock else cfa_chrome._reviewer_bottom_css()
    return (
        "<!doctype html><html><head><meta charset=utf-8>"
        f"<style>{_base_css()}</style>{chrome_css}</head>"
        f"<body>{_bottom_body(question=question)}</body></html>"
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    stock = "--stock" in args
    question = "--question" in args
    positional = [a for a in args if not a.startswith("--")]
    out = positional[0] if positional else os.path.join(_HERE, "reviewer-bottom.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build_html(stock=stock, question=question))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
