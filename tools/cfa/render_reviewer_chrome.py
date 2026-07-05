"""Render before/after proof of the CFA main-reviewer chrome (D-P4-14).

Reconstructs the Anki reviewer body DOM — a card sitting on the reviewer page,
plus a type-in-answer diff (typeGood / typeBad / typeMissed) — over the real
stock reviewer CSS, then overlays the exact `_reviewer_css()` the app injects,
so the shipped reskin is faithfully shown without launching Anki. Writes
reviewer-{before,after}.html into proof/reviewer-chrome/.
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

# A card that doesn't paint its own background + a type-in-answer diff row, so
# both the page-tint change and the retoned feedback colours are visible.
BODY = """
  <div id="qa" dir="auto">
    <div class="card">
      <div style="font-size:14px;letter-spacing:.14em;text-transform:uppercase;color:#DA5C01;font-weight:700;">
        ankiCFA &middot; Type the answer
      </div>
      <p style="color:#4D5C6D;">Spell the CFA Standard code for material nonpublic information.</p>
      <div class="type">
        <span class="typeGood">II(A</span><span class="typeBad">x</span><span class="typeMissed">)</span>
      </div>
    </div>
  </div>
"""


def _page(title: str, extra_head: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset=utf-8><title>{title}</title>"
        f"<style>{STOCK_CSS}</style>{extra_head}</head>"
        f"<body>{BODY}</body></html>"
    )


def main() -> None:
    out = os.path.join(_ROOT, "proof/reviewer-chrome")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "reviewer-before.html"), "w") as f:
        f.write(_page("Reviewer body — stock Anki (before)", ""))
    with open(os.path.join(out, "reviewer-after.html"), "w") as f:
        f.write(_page("Reviewer body — CFA chrome (after)", cfa_chrome._reviewer_css()))
    print("wrote reviewer-before.html / reviewer-after.html to", out)


if __name__ == "__main__":
    main()
