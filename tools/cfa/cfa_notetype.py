#!/usr/bin/env python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A CFA-branded note type for the hand-authored CFA Level II knowledge deck.

The 630-card knowledge deck used to ride the stock ``Basic`` note type, so the
single surface a candidate spends the most time on -- the flashcard face during
"Study by Exam Priority" -- rendered in stock-Anki Arial/centred/black-on-white
and read as plain Anki, not as a purpose-built CFA product.

This module defines one note type, :data:`CFA_NOTETYPE_NAME`, whose Front/Back
templates and CSS match the CFA design system (the same tokens the desktop
dialogs, the ethics card, and the SvelteKit pages use). Because the CSS/templates
live *in the note type*, they travel with the collection: every desktop review,
every synced device, and the exported ``.apkg`` the phone imports all get the
identical CFA-styled card face -- one design system, no per-platform work.

The note type keeps the same two fields as ``Basic`` (``Front`` / ``Back``) so
the deck builder, the exam-queue join key, and the memory score are unchanged;
only the presentation is branded.
"""

from __future__ import annotations

from typing import Any

CFA_NOTETYPE_NAME = "CFA Knowledge"

# The card face. A quiet accent eyebrow anchors the CFA identity, the prompt is
# the serif "hero" (matching the ethics card + the SvelteKit pages), and the
# answer sits below a calm brand-line rule. {{Back}} already carries the
# authored answer + the named-source footer span (build_cfa_deck.back_with_source).
_FRONT_TMPL = """<div class="cfa-card">
  <div class="cfa-eyebrow">ankiCFA · Level II</div>
  <div class="cfa-prompt">{{Front}}</div>
</div>"""

_BACK_TMPL = """<div class="cfa-card">
  <div class="cfa-eyebrow">ankiCFA · Level II</div>
  <div class="cfa-prompt">{{Front}}</div>
  <hr id="answer" class="cfa-rule">
  <div class="cfa-answer">{{Back}}</div>
</div>"""

# CFA design tokens (mirrors cfa/ethics_pairs/templates/style.css :root and the
# desktop qt/aqt/cfa_style.py TOKENS). Fonts fall back through the system stack
# so a card renders correctly even where the bundled OFL faces are unavailable.
_CSS = """:root {
  --cfa-ink: #122B46;
  --cfa-muted: #4D5C6D;
  --cfa-faint: #68707d;
  --cfa-line: #E7E9EC;
  --cfa-surface: #F3F6F8;
  --cfa-accent: #DA5C01;
  --cfa-font: "IBM Plex Sans", -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --cfa-font-heading: "Source Serif 4", Georgia, "Times New Roman", serif;
}

.card {
  font-family: var(--cfa-font);
  font-size: 19px;
  background: #FFFFFF;
  -webkit-font-smoothing: antialiased;
  padding: 0;
}
.nightMode.card { background: #1c1f24; }

.cfa-card {
  max-width: 720px;
  margin: 0 auto;
  padding: 28px 22px 32px;
  text-align: left;
  color: var(--cfa-ink);
  line-height: 1.62;
}
.nightMode .cfa-card { color: #e8ecf1; }

/* Quiet uppercase brand over-line. */
.cfa-eyebrow {
  font-family: var(--cfa-font);
  font-size: .72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .12em;
  color: var(--cfa-accent);
  margin-bottom: 14px;
}

/* The prompt is the serif hero, matching every other CFA surface. */
.cfa-prompt {
  font-family: var(--cfa-font-heading);
  font-weight: 400;
  font-size: 1.38rem;
  line-height: 1.32;
  color: var(--cfa-ink);
}
.nightMode .cfa-prompt { color: #f2f5f8; }

/* Calm brand-line divider between prompt and answer (replaces the stock <hr>). */
.cfa-rule {
  border: none;
  border-top: 1px solid var(--cfa-line);
  margin: 22px 0;
}
.nightMode .cfa-rule { border-top-color: #2b323b; }

.cfa-answer { color: var(--cfa-ink); }
.nightMode .cfa-answer { color: #e8ecf1; }

/* The named-source provenance footer (build_cfa_deck.render_source_line). */
.cfa-source {
  display: inline-block;
  margin-top: 6px;
  font-family: var(--cfa-font);
  font-size: .78rem;
  font-weight: 500;
  letter-spacing: .01em;
  color: var(--cfa-faint);
}
.nightMode .cfa-source { color: #8b95a3; }
"""


def build_cfa_notetype(col: Any) -> Any:
    """Return a fresh, unsaved CFA-branded note type (Front/Back + CFA CSS)."""
    nt = col.models.new(CFA_NOTETYPE_NAME)
    for field_name in ("Front", "Back"):
        col.models.add_field(nt, col.models.new_field(field_name))
    tmpl = col.models.new_template("CFA Card")
    tmpl["qfmt"] = _FRONT_TMPL
    tmpl["afmt"] = _BACK_TMPL
    col.models.add_template(nt, tmpl)
    nt["css"] = _CSS
    return nt


def ensure_cfa_notetype(col: Any) -> Any:
    """Idempotently return the saved CFA-branded note type.

    If a note type named :data:`CFA_NOTETYPE_NAME` already exists (e.g. a prior
    seed/build), its CSS + templates are refreshed to the current design so a
    re-run picks up branding changes; otherwise it is created.
    """
    existing = col.models.by_name(CFA_NOTETYPE_NAME)
    if existing is not None:
        # Refresh presentation on re-run so branding stays current, but keep the
        # id/fields stable so existing notes are untouched.
        existing["css"] = _CSS
        if existing["tmpls"]:
            existing["tmpls"][0]["qfmt"] = _FRONT_TMPL
            existing["tmpls"][0]["afmt"] = _BACK_TMPL
        col.models.update_dict(existing)
        return col.models.by_name(CFA_NOTETYPE_NAME)
    nt = build_cfa_notetype(col)
    col.models.add(nt)
    return col.models.by_name(CFA_NOTETYPE_NAME)
