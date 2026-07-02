# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Definition + idempotent installer for the "CFA Ethics Minimal-Pair" note type.

Depends on ``anki`` only inside :func:`ensure_notetype` (which is given a live ``Collection``);
the constants and template loading are import-safe without a built pylib.

The note type is deliberately template-driven: the interactive review flow lives entirely in the
card templates (``templates/front.html`` + ``templates/back.html`` + ``templates/style.css``), so it
renders on desktop and, through the shared collection/sync, on AnkiMobile/AnkiDroid too. No Rust,
no backend changes.
"""

from __future__ import annotations

import os

NOTETYPE_NAME = "CFA Ethics Minimal-Pair"
TEMPLATE_NAME = "Contrastive Pair"
DECK_NAME = "CFA::Ethics Pairs"

# Field order is significant: PairId is the sort field. These names are the contract the card
# templates ({{PairId}}, {{VignetteA}}, ...) and the importer rely on.
#
# The review flow is an in-vignette HIGHLIGHT interaction: the learner highlights the decisive
# phrase directly in the paragraph. ``DecisivePhrase`` is the EXACT verbatim substring of the
# relevant vignette that flips the answer, and ``DecisivePhraseCase`` ("A"/"B") says which vignette
# holds it. The legacy ``DecisiveFact``/``DistractorFact*`` fields are kept (additive-only) so
# existing notes and the importer round-trip test stay valid.
FIELDS = [
    "PairId",
    "ClusterTag",
    "VignetteA",
    "VignetteB",
    "AnswerA",
    "AnswerB",
    "DecisiveFact",
    "DecisivePhrase",
    "DecisivePhraseCase",
    "DistractorFact1",
    "DistractorFact2",
    "DistractorFact3",
    "Standard",
    "Rationale",
]

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def _read(name: str) -> str:
    with open(os.path.join(_TEMPLATE_DIR, name), encoding="utf-8") as f:
        return f.read()


def load_templates() -> tuple[str, str, str]:
    """Return (front_html, back_html, css) read from the templates/ directory."""
    return _read("front.html"), _read("back.html"), _read("style.css")


def ensure_notetype(col):
    """Create the note type if missing, or refresh its templates/CSS if it already exists.

    Returns the persisted notetype dict. Re-running is safe and picks up template edits, which
    makes iterating on the card UI painless during development.
    """
    front, back, css = load_templates()
    existing = col.models.by_name(NOTETYPE_NAME)
    if existing is not None:
        # Refresh presentation in place and additively add any fields missing from an older install
        # (e.g. DecisivePhrase/DecisivePhraseCase). Adding fields is non-destructive: existing notes
        # simply get the new fields empty until re-imported.
        present = {f["name"] for f in existing["flds"]}
        for name in FIELDS:
            if name not in present:
                col.models.add_field(existing, col.models.new_field(name))
        existing["css"] = css
        if existing["tmpls"]:
            existing["tmpls"][0]["qfmt"] = front
            existing["tmpls"][0]["afmt"] = back
        col.models.update_dict(existing)
        return col.models.by_name(NOTETYPE_NAME)

    nt = col.models.new(NOTETYPE_NAME)
    for name in FIELDS:
        col.models.add_field(nt, col.models.new_field(name))
    col.models.set_sort_index(nt, 0)  # sort by PairId

    tmpl = col.models.new_template(TEMPLATE_NAME)
    tmpl["qfmt"] = front
    tmpl["afmt"] = back
    col.models.add_template(nt, tmpl)
    nt["css"] = css

    col.models.add(nt)
    return col.models.by_name(NOTETYPE_NAME)
