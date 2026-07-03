#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render REAL before/after proof of the F3 "AI Back" tab-to-fill feature using
the LIVE LLM.

Unlike ``render_f3_tab_fill.py`` (which routes an offline *mocked* completion
through the real ``fill_note_back`` for a deterministic offline artifact), this
driver makes a genuine network call: it invokes
``aqt.cfa_tab_fill.fill_note_back(note)`` with NO injected ``complete_fn`` so the
default path — ``cfa.ai.llm_client.complete`` — actually runs. Therefore:

* the AFTER back text is a real, run-to-run-varying LLM draft (never hardcoded);
* the ``ai-generated`` provenance tag shown is the tag that same real call added.

Two single-card states are emitted as standalone HTML (screenshot separately):

  1. BEFORE — front filled, back empty, enabled "AI Back" button. NO LLM call.
  2. AFTER  — ``fill_note_back`` drafted the back with the real LLM and tagged
              the note ``ai-generated``.

Security: the OpenAI key is never read, printed, or embedded here; it is only
used inside ``llm_client`` and is never returned in any result or written to the
emitted HTML.

Requires ``OPENAI_API_KEY`` (gitignored ``.env``). Run:

    set -a; . ./.env; set +a
    PYTHONPATH="out/pylib:pylib:qt:out/qt:." QT_QPA_PLATFORM=offscreen \\
      out/pyenv/bin/python tools/cfa/render_f3_tab_fill_withkey.py \\
      --before proof/fixes/p4/f3-withkey-before.html \\
      --after  proof/fixes/p4/f3-withkey-after.html
"""

from __future__ import annotations

import argparse
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
# `import render_f3_tab_fill` (sibling), `aqt.*` (qt/), and `cfa.*` (repo root).
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "qt"))
sys.path.insert(0, REPO)

from aqt.cfa_tab_fill import AI_TAG, fill_note_back  # noqa: E402

# Reuse the exact FRONT question, note stub, and enabled-button markup from the
# offline renderer so the two proofs are directly comparable.
from render_f3_tab_fill import FRONT, _ENABLED_BTN, _Note  # noqa: E402

FMT = "".join(f'<div class="fmt">{c}</div>' for c in ("B", "I", "U", "{}"))

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background:#f4f5f7;
         margin:0; padding:20px; color:#1b1d21; }}
  .panel {{ background:#fff; border:1px solid #d9dce1; border-radius:10px; width:352px;
            box-shadow:0 1px 3px rgba(0,0,0,.06); overflow:hidden; margin:0 auto; }}
  .cap {{ font-size:12px; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
          padding:9px 14px; border-bottom:1px solid #e6e8ec; }}
  .cap.before {{ color:#6b7280; background:#f8f9fb; }}
  .cap.after  {{ color:#166534; background:#ecfdf3; }}
  .toolbar {{ display:flex; align-items:center; gap:6px; padding:8px 12px;
              border-bottom:1px solid #eceef1; background:#fafbfc; }}
  .fmt {{ width:22px; height:22px; border:1px solid #dfe2e7; border-radius:5px; background:#fff;
          font-size:12px; color:#8a909a; display:flex; align-items:center; justify-content:center; }}
  .anki-addon-button {{ margin-left:auto; padding:4px 12px; font-size:13px; font-weight:600;
          border:1px solid #c7ccff; border-radius:6px; background:#eef0ff; color:#3730a3; cursor:pointer; }}
  .field {{ padding:12px 14px; }}
  .flabel {{ font-size:11px; font-weight:700; color:#8a909a; text-transform:uppercase;
             letter-spacing:.05em; margin-bottom:5px; }}
  .fbox {{ border:1px solid #dfe2e7; border-radius:7px; padding:9px 11px; font-size:13.5px;
           line-height:1.5; min-height:22px; background:#fff; }}
  .fbox.empty {{ color:#b6bbc3; font-style:italic; }}
  .fbox.filled {{ background:#f7fff9; border-color:#bbf7d0; }}
  .tags {{ padding:10px 14px; border-top:1px solid #eceef1; font-size:12px; color:#6b7280;
           display:flex; align-items:center; gap:8px; }}
  .tag {{ background:#dcfce7; color:#166534; border:1px solid #86efac; border-radius:12px;
          padding:2px 10px; font-weight:600; }}
  .meta {{ margin:14px auto 0; font-size:11px; color:#8a909a; text-align:center; max-width:352px; }}
</style></head><body>
  <div class="panel">
    <div class="cap {capclass}">{caption}</div>
    <div class="toolbar">{fmt}{enabled_btn}</div>
    <div class="field"><div class="flabel">Front</div><div class="fbox">{front}</div></div>
    <div class="field"><div class="flabel">Back</div><div class="fbox {backclass}">{back}</div></div>
    <div class="tags">Tags: {tags}</div>
  </div>
  <div class="meta">{meta}</div>
</body></html>"""


def _write(path: str, doc: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)


def render_before(out_path: str) -> None:
    """BEFORE: front filled, back empty, enabled button — no LLM call at all."""
    doc = PAGE.format(
        capclass="before",
        caption="Before &mdash; back empty, AI Back ready",
        fmt=FMT,
        enabled_btn=_ENABLED_BTN,
        front=html.escape(FRONT),
        backclass="empty",
        back="(empty)",
        tags='<span style="color:#b6bbc3">(none)</span>',
        meta="Real editor button markup. No LLM call is made in this state.",
    )
    _write(out_path, doc)
    print(f"wrote {out_path} (before; no LLM call)")


def render_after(out_path: str) -> str:
    """AFTER: drive the REAL LLM via fill_note_back and render the genuine draft."""
    note = _Note()
    # No complete_fn -> aqt.cfa_tab_fill falls through to the real
    # cfa.ai.llm_client.complete (a live OpenAI call).
    res = fill_note_back(note)
    assert res["ok"] and res["status"] == "filled", res
    assert AI_TAG in note.tags, note.tags
    back = note.fields[1]
    assert back.strip(), "real LLM returned an empty back"

    model = res.get("model") or ""
    doc = PAGE.format(
        capclass="after",
        caption="After &mdash; drafted by real LLM, tagged",
        fmt=FMT,
        enabled_btn=_ENABLED_BTN,
        front=html.escape(FRONT),
        backclass="filled",
        back=html.escape(back),
        tags=f'<span class="tag">{html.escape(AI_TAG)}</span>',
        meta=(
            "Back drafted LIVE via aqt.cfa_tab_fill.fill_note_back() &rarr; "
            f"cfa.ai.llm_client.complete (model {html.escape(model)}); "
            f"{len(back)} chars. Content varies run-to-run."
        ),
    )
    _write(out_path, doc)
    print(f"wrote {out_path} (after; real LLM draft, model={model})")
    print(f"tags after fill: {note.tags}")
    print(f"real drafted back ({len(back)} chars):\n{back}")
    return back


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F3 with-key (real LLM) before/after proof")
    ap.add_argument(
        "--before", default=os.path.join(REPO, "proof", "fixes", "p4", "f3-withkey-before.html")
    )
    ap.add_argument(
        "--after", default=os.path.join(REPO, "proof", "fixes", "p4", "f3-withkey-after.html")
    )
    args = ap.parse_args(argv)

    render_before(args.before)
    render_after(args.after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
