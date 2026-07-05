# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Regression guard for the D4 (Ethics reviewer) Phase-B Pass-2 fix.

A decisive gold phrase is several adjacent ``.cfa-tok`` spans. The reveal used to
outline EVERY gold token with a full four-sided ``box-shadow`` inset, so a
multi-word answer-key phrase rendered as a ladder of disconnected word-boxes
(interior vertical dividers between every word) instead of one continuous
highlighted span. The fix (``templates/style.css``) composes the outline from
four inset EDGE rules and OPENS the interior edges between contiguous gold tokens
via the ``.cfa-tok.gold + .cfa-tok.gold`` (left) and
``.cfa-tok.gold:has(+ .cfa-tok.gold)`` (right) selectors, so a run reads as one
outlined phrase while a lone gold token stays a full rounded pill.

This is a presentation-only change to ``style.css`` (NOT the byte-mirrored shared
JS grader, so ``test_highlight.py`` is untouched). This stdlib test locks the fix
so it cannot silently revert to the per-token box.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = os.path.join(os.path.dirname(HERE), "templates", "style.css")


def _css() -> str:
    with open(CSS, encoding="utf-8") as f:
        return f.read()


def test_old_per_token_full_box_is_gone():
    """The old single four-sided box (fragments a phrase into per-word boxes) is removed."""
    css = _css()
    assert "0 0 0 2px var(--cfa-brand-green) inset" not in css
    assert "0 0 0 2px #56c98a inset" not in css


def test_gold_run_edge_selectors_present():
    """The continuous-run outline is composed from edge-aware selectors."""
    css = _css()
    # left edge opened when a gold token precedes this one (mid/end of a run)
    assert ".cfa-tok.gold + .cfa-tok.gold" in css
    # right edge opened when a gold token follows this one (start/mid of a run)
    assert ".cfa-tok.gold:has(+ .cfa-tok.gold)" in css
    # interior of a run (gold on both sides) → top + bottom rules only
    assert ".cfa-tok.gold + .cfa-tok.gold:has(+ .cfa-tok.gold)" in css


def test_base_gold_is_four_inset_edge_rules():
    """A lone gold token still draws all four green edges (a full rounded pill)."""
    css = _css()
    # isolate the base `.cfa-tok.gold { ... }` block (not the ` + ` / `:has` variants)
    m = re.search(r"\n\.cfa-tok\.gold\s*\{([^}]*)\}", css)
    assert m, "base .cfa-tok.gold rule not found"
    block = m.group(1)
    # four inset edge rules: top, bottom, left, right
    assert block.count("inset") == 4
    assert "inset 0 2px 0 0 var(--cfa-brand-green)" in block  # top
    assert "inset 0 -2px 0 0 var(--cfa-brand-green)" in block  # bottom
    assert "inset 2px 0 0 0 var(--cfa-brand-green)" in block  # left
    assert "inset -2px 0 0 0 var(--cfa-brand-green)" in block  # right
    assert "border-radius: 4px" in block


def test_night_mode_run_variants_present():
    """The dark-theme reveal gets the same continuous-run treatment (no ladder at night)."""
    css = _css()
    assert ".nightMode .cfa-tok.gold + .cfa-tok.gold" in css
    assert ".nightMode .cfa-tok.gold:has(+ .cfa-tok.gold)" in css


def test_interior_rule_is_top_and_bottom_only():
    """A middle-of-run token draws only top+bottom rules (no vertical dividers)."""
    css = _css()
    m = re.search(
        r"\.cfa-tok\.gold \+ \.cfa-tok\.gold:has\(\+ \.cfa-tok\.gold\)\s*\{([^}]*)\}",
        css,
    )
    assert m, "interior-of-run rule not found"
    block = m.group(1)
    assert block.count("inset") == 2  # top + bottom only, no left/right
    assert "border-radius: 0" in block
