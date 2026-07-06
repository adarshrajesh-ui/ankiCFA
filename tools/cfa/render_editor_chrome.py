# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render before/after proof of the CFA editor chrome (D-P4-13).

Reconstructs the Anki note-editor DOM (Front/Back field cards + labels + the
tab-fill affordance) over the real stock editor CSS variables, then overlays the
exact `_editor_css()` the app injects, so the shipped reskin is faithfully shown
without launching Anki. Writes editor-{before,after}.html into proof/editor-chrome/.
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

# Stock Anki editor light-theme variables (approx values from ts/lib theme).
STOCK_VARS = """
  :root {
    --canvas: #ffffff;
    --canvas-elevated: #f7f8f9;
    --fg: #2a2a2a;
    --border: #d7d7d7;
    --border-focus: #4899e8;   /* stock blue focus ring */
    --border-radius: 5px;
  }
  html, body { background: var(--canvas-elevated); font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color: var(--fg); margin: 0; }
"""

# The editor DOM (light-DOM classes cfa_chrome targets), with the tab-fill hint.
BODY = """
  <div class="fields" style="padding:22px 26px; max-width:560px;">
    <div class="field-container">
      <div class="label-container"><span class="label-name">Front</span></div>
      <div class="editor-field"><div class="content">What is the CAPM expected return formula?</div></div>
    </div>
    <div style="height:16px"></div>
    <div class="field-container">
      <div class="label-container"><span class="label-name">Back</span></div>
      <div class="editor-field focus"><div class="content hint">&#10022; Press <b>Tab</b> to generate this with AI</div></div>
    </div>
  </div>
"""

FIELD_CSS = """
  .field-container { background: var(--canvas); border-radius: var(--border-radius); overflow:hidden; }
  .label-container { padding: 0 3px 4px; }
  .label-name { font-size: 13px; }
  .editor-field { border: 1px solid var(--border); border-radius: var(--border-radius); margin:1px; padding:12px 14px; box-shadow:0 1px 2px rgba(0,0,0,.06); background:var(--canvas); }
  .editor-field.focus { outline: 2px solid var(--border-focus); outline-offset:-1px; }
  .content { font-size:15px; line-height:1.5; }
  .hint { color:#8a8f96; }
"""


def _page(title: str, extra_head: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset=utf-8><title>{title}</title>"
        f"<style>{STOCK_VARS}{FIELD_CSS}</style>{extra_head}</head>"
        f"<body>{BODY}</body></html>"
    )


def main() -> None:
    out = os.path.join(_ROOT, "proof/editor-chrome")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "editor-before.html"), "w") as f:
        f.write(_page("Editor — stock Anki (before)", ""))
    # After: the injected CFA css wins the cascade; make the accent ring visible
    # by mapping .editor-field.focus onto the shipped :focus-within rule.
    after_head = cfa_chrome._editor_css() + (
        "<style>.editor-field.focus{outline-color:#DA5C01 !important;}</style>"
    )
    with open(os.path.join(out, "editor-after.html"), "w") as f:
        f.write(_page("Editor — CFA chrome (after)", after_head))
    print("wrote editor-before.html / editor-after.html to", out)


if __name__ == "__main__":
    main()
