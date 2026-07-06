# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render before/after proof of the CFA main-reviewer chrome (D-P4-14).

Reconstructs the Anki reviewer body DOM — an unbranded Basic-style CFA card
sitting on the reviewer page, plus a type-in-answer diff (typeGood / typeBad /
typeMissed) — over the real stock reviewer CSS, then overlays the exact
`_reviewer_css()` + Basic-card wrapper the app injects, so the shipped reskin is
faithfully shown without launching Anki. Writes reviewer-{before,after}.html
into proof/reviewer-chrome/.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [
    os.path.join(_ROOT, "out/pylib"),
    os.path.join(_ROOT, "pylib"),
    os.path.join(_ROOT, "qt"),
    os.path.join(_ROOT, "out/qt"),
]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt import cfa_chrome  # noqa: E402

# Stock Anki reviewer light-theme CSS (the relevant slice of ts/reviewer.scss).
STOCK_CSS = """
  html, body { margin: 0; background: #ffffff; color: #2a2a2a;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }
  #qa { text-align: center; padding: 40px 20px; }
  .card { font-size: 20px; }
  .typeGood { background: #afa; color: black; }
  .typeBad  { background: #faa; color: black; }
  .typeMissed { background: #ccc; color: black; }
  .type { font-size: 22px; letter-spacing: .02em; }
  .type span { padding: 0 1px; border-radius: 2px; }
"""

# A Basic card that doesn't paint its own background, matching the screenshot
# regression, plus a type-in-answer diff row so feedback colors stay visible.
BASIC_CARD = """
<div class="card">
  <p>Name the three factors in the Fama-French model.</p>
  <div class="type">
    <span class="typeGood">Mkt</span><span class="typeBad">x</span><span class="typeMissed">SMB</span>
  </div>
</div>
"""


def _body(card_html: str) -> str:
    return f"""
  <div id="qa" dir="auto">
    {card_html}
  </div>
"""


def _page(title: str, extra_head: str, card_html: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset=utf-8><title>{title}</title>"
        f"<style>{STOCK_CSS}</style>{extra_head}</head>"
        f"<body>{_body(card_html)}</body></html>"
    )


def main() -> None:
    out = os.path.join(_ROOT, "proof/reviewer-chrome")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "reviewer-before.html"), "w") as f:
        f.write(_page("Reviewer body — stock Anki (before)", "", BASIC_CARD))
    with open(os.path.join(out, "reviewer-after.html"), "w") as f:
        wrapped = cfa_chrome._wrap_basic_cfa_card(BASIC_CARD, "reviewQuestion")
        f.write(
            _page(
                "Reviewer body — CFA chrome (after)",
                cfa_chrome._reviewer_css(),
                wrapped,
            )
        )
    print("wrote reviewer-before.html / reviewer-after.html to", out)


if __name__ == "__main__":
    main()
