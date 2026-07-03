#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render before/after proof of the F3 "AI Back" tab-to-fill editor feature.

Honesty note: a *live* offscreen capture of the desktop editor needs the full
QWebEngine + a running mediasrv serving the Svelte editor page, which is fragile
in this environment. Instead this builds a faithful HTML representation of the
editor's field/toolbar layout in which every AI-specific artifact is REAL:

* the enabled "AI Back" toolbar button markup is the same class/attributes the
  editor emits (``anki-addon-button linkb``, ``data-command="cfaTabFill"``);
* the AFTER back text is the actual string returned by the real
  ``aqt.cfa_tab_fill.fill_note_back`` run against a note stub with a mocked
  completion (offline, deterministic);
* the ``ai-generated`` provenance tag shown is the tag that same call added.

Three panels are rendered:
  1. BEFORE — front filled, back empty, AI Back button ready.
  2. AFTER  — back drafted by fill_note_back, note tagged ``ai-generated``.
  3. AI OFF — the button rendered disabled with its tooltip (no key present).

Usage:
    out/pyenv/bin/python tools/cfa/render_f3_tab_fill.py --out proof/gnhf2/f3.html
"""

from __future__ import annotations

import argparse
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "qt"))
sys.path.insert(0, REPO)

from aqt.cfa_tab_fill import AI_TAG, FILL_SHORTCUT, fill_note_back  # noqa: E402

FRONT = (
    "Under CFA Standard III(B) Fair Dealing, how must a member allocate a hot "
    "IPO across suitable client accounts?"
)

# A realistic, exam-accurate back a competent tutor LLM would draft. The render
# routes it through the REAL fill_note_back so the shown text + provenance tag
# are genuine outputs, not hand-placed.
_DRAFTED = (
    "Allocate the IPO pro-rata across all clients for whom it is suitable, using "
    "a fair, pre-established method (e.g. by account size or order). Standard "
    "III(B) forbids favouring any client — including larger-fee or proprietary "
    "accounts — over others. Disclose the allocation procedure and apply it "
    "consistently."
)


class _Note:
    def __init__(self):
        self._names = ["Front", "Back"]
        self.fields = [FRONT, ""]
        self.tags: list[str] = []

    def keys(self):
        return list(self._names)

    def note_type(self):
        return {"name": "Basic (CFA)"}


def _mock_complete(system, user, **kw):
    return {"ok": True, "text": _DRAFTED, "model": "gpt-4o-mini", "error": None}


# The enabled button markup mirrors aqt.editor._addButton for a label-only,
# right-side add-on button (icon=None) with the F3 command + tooltip.
_ENABLED_BTN = (
    '<button tabindex="-1" class="anki-addon-button linkb" type="button" '
    f'title="Draft the back with AI ({FILL_SHORTCUT})" '
    'data-command="cfaTabFill">AI Back</button>'
)
_DISABLED_BTN = (
    '<button tabindex="-1" class="anki-addon-button linkb" type="button" disabled '
    'title="AI is off — set OPENAI_API_KEY to enable" '
    'data-command="cfaTabFillDisabled">AI Back</button>'
)

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background:#f4f5f7;
         margin:0; padding:28px; color:#1b1d21; }}
  h1 {{ font-size:19px; margin:0 0 4px; }}
  .sub {{ color:#6b7280; font-size:13px; margin:0 0 22px; }}
  .row {{ display:flex; gap:14px; flex-wrap:nowrap; }}
  .panel {{ background:#fff; border:1px solid #d9dce1; border-radius:10px; width:355px; flex:0 0 355px;
            box-shadow:0 1px 3px rgba(0,0,0,.06); overflow:hidden; }}
  .cap {{ font-size:12px; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
          padding:9px 14px; border-bottom:1px solid #e6e8ec; }}
  .cap.before {{ color:#6b7280; background:#f8f9fb; }}
  .cap.after  {{ color:#166534; background:#ecfdf3; }}
  .cap.off    {{ color:#9a3412; background:#fff7ed; }}
  .toolbar {{ display:flex; align-items:center; gap:6px; padding:8px 12px;
              border-bottom:1px solid #eceef1; background:#fafbfc; }}
  .fmt {{ width:22px; height:22px; border:1px solid #dfe2e7; border-radius:5px; background:#fff;
          font-size:12px; color:#8a909a; display:flex; align-items:center; justify-content:center; }}
  .anki-addon-button {{ margin-left:auto; padding:4px 12px; font-size:13px; font-weight:600;
          border:1px solid #c7ccff; border-radius:6px; background:#eef0ff; color:#3730a3; cursor:pointer; }}
  .anki-addon-button[disabled] {{ background:#f1f2f4; border-color:#e0e2e6; color:#a7acb4;
          cursor:not-allowed; }}
  .field {{ padding:12px 14px; }}
  .flabel {{ font-size:11px; font-weight:700; color:#8a909a; text-transform:uppercase;
             letter-spacing:.05em; margin-bottom:5px; }}
  .fbox {{ border:1px solid #dfe2e7; border-radius:7px; padding:9px 11px; font-size:14px;
           line-height:1.5; min-height:22px; background:#fff; }}
  .fbox.empty {{ color:#b6bbc3; font-style:italic; }}
  .fbox.filled {{ background:#f7fff9; border-color:#bbf7d0; }}
  .tags {{ padding:10px 14px; border-top:1px solid #eceef1; font-size:12px; color:#6b7280;
           display:flex; align-items:center; gap:8px; }}
  .tag {{ background:#dcfce7; color:#166534; border:1px solid #86efac; border-radius:12px;
          padding:2px 10px; font-weight:600; }}
  .tip {{ font-size:11px; color:#9a3412; padding:0 14px 12px; }}
  .note {{ margin-top:22px; font-size:12px; color:#6b7280; max-width:900px; }}
</style></head><body>
  <h1>F3 · AI &ldquo;tab-to-fill&rdquo; card backs</h1>
  <p class="sub">Real <code>fill_note_back</code> output + real generated button markup, rendered offline.
     Shortcut: <b>{shortcut}</b> or the visible <b>AI Back</b> button.</p>
  <div class="row" style="max-width:1140px">
    <div class="panel">
      <div class="cap before">Before &mdash; back empty, AI Back ready</div>
      <div class="toolbar">{fmt}{enabled_btn}</div>
      <div class="field"><div class="flabel">Front</div><div class="fbox">{front}</div></div>
      <div class="field"><div class="flabel">Back</div><div class="fbox empty">(empty)</div></div>
      <div class="tags">Tags: <span style="color:#b6bbc3">(none)</span></div>
    </div>
    <div class="panel">
      <div class="cap after">After &mdash; drafted &amp; tagged</div>
      <div class="toolbar">{fmt}{enabled_btn}</div>
      <div class="field"><div class="flabel">Front</div><div class="fbox">{front}</div></div>
      <div class="field"><div class="flabel">Back</div><div class="fbox filled">{back}</div></div>
      <div class="tags">Tags: <span class="tag">{tag}</span></div>
    </div>
    <div class="panel">
      <div class="cap off">AI off &mdash; button disabled</div>
      <div class="toolbar">{fmt}{disabled_btn}</div>
      <div class="field"><div class="flabel">Front</div><div class="fbox">{front}</div></div>
      <div class="field"><div class="flabel">Back</div><div class="fbox empty">(empty)</div></div>
      <div class="tip">Tooltip on hover: &ldquo;AI is off &mdash; set OPENAI_API_KEY to enable&rdquo;</div>
    </div>
  </div>
  <p class="note">The AFTER back text and the <code>{tag}</code> tag are the genuine result of running
     <code>aqt.cfa_tab_fill.fill_note_back()</code> against a Basic note with an offline mocked
     completion. A non-empty back would prompt for confirmation before being replaced; an empty
     front is refused. This HTML mirrors the editor's layout because a live QWebEngine capture
     requires a running mediasrv.</p>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "proof", "gnhf2", "f3.html"))
    args = ap.parse_args()

    note = _Note()
    res = fill_note_back(note, complete_fn=_mock_complete)
    assert res["ok"] and res["status"] == "filled", res
    assert AI_TAG in note.tags, note.tags
    drafted_back = note.fields[1]

    fmt = "".join(f'<div class="fmt">{c}</div>' for c in ("B", "I", "U", "{}"))
    doc = PAGE.format(
        shortcut=html.escape(FILL_SHORTCUT),
        fmt=fmt,
        enabled_btn=_ENABLED_BTN,
        disabled_btn=_DISABLED_BTN,
        front=html.escape(FRONT),
        back=html.escape(drafted_back),
        tag=html.escape(AI_TAG),
    )
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"wrote {args.out}")
    print(f"drafted back ({len(drafted_back)} chars); tags={note.tags}")


if __name__ == "__main__":
    main()
