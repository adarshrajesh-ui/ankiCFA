# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F5 tests: the shared CFA design system.

Covers the token table, the QSS + HTML builders in ``aqt.cfa_style``, the
palette-parity invariant between the Python tokens and the ethics card's
``:root`` block (the whole point of F5 — ONE palette across every surface), and
that both real dialogs actually adopt the shared chrome.
"""

from __future__ import annotations

import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from aqt import cfa_style

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARD_CSS = os.path.join(REPO, "cfa", "ethics_pairs", "templates", "style.css")

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


# --------------------------------------------------------------------------
# Token table
# --------------------------------------------------------------------------


def test_tokens_have_the_core_palette():
    for key in (
        "ink",
        "muted",
        "line",
        "surface",
        "bg",
        "primary",
        "pass",
        "fail",
        "warn",
        "accent",
    ):
        assert key in cfa_style.TOKENS, key


def test_color_tokens_are_valid_hex():
    color_keys = [
        "ink",
        "muted",
        "faint",
        "line",
        "surface",
        "bg",
        "primary",
        "primary_soft",
        "primary_hover",
        "pass",
        "pass_soft",
        "fail",
        "fail_soft",
        "warn",
        "accent",
        "accent_soft",
    ]
    for key in color_keys:
        assert _HEX.match(cfa_style.TOKENS[key]), f"{key}={cfa_style.TOKENS[key]!r}"


def test_type_scale_is_a_descending_ordered_ramp():
    title = int(cfa_style.TOKENS["fs_title"])
    lead = int(cfa_style.TOKENS["fs_lead"])
    body = int(cfa_style.TOKENS["fs_body"])
    meta = int(cfa_style.TOKENS["fs_meta"])
    eyebrow = int(cfa_style.TOKENS["fs_eyebrow"])
    assert title > lead > body > meta >= eyebrow


# --------------------------------------------------------------------------
# QSS
# --------------------------------------------------------------------------


def test_dialog_qss_carries_the_palette():
    qss = cfa_style.dialog_qss()
    assert cfa_style.PRIMARY in qss
    assert cfa_style.LINE in qss
    assert "QTableWidget" in qss
    assert "QPushButton" in qss
    assert "QHeaderView::section" in qss


# --------------------------------------------------------------------------
# HTML builders
# --------------------------------------------------------------------------


def test_hero_uses_pass_palette_when_passed():
    html = cfa_style.hero(
        call="likely pass",
        call_prob=0.87,
        passed=True,
        lead_html="lead",
        note_html="note",
    )
    assert cfa_style.PASS in html
    assert cfa_style.FAIL not in html
    assert "likely pass" in html
    assert "p=0.87" in html


def test_hero_uses_fail_palette_when_not_passed():
    html = cfa_style.hero(
        call="likely fail",
        call_prob=0.22,
        passed=False,
        lead_html="lead",
        note_html="note",
    )
    assert cfa_style.FAIL in html
    assert cfa_style.PASS not in html


def test_band_shows_name_meaning_and_value():
    html = cfa_style.band(
        name="Memory", meaning="recall probability", value_html="60%–80%"
    )
    assert "Memory" in html
    assert "recall probability" in html
    assert "60%–80%" in html


def test_value_abstain_flags_missing_data():
    assert "Not enough data" in cfa_style.value_abstain("too few reviews")


def test_eyebrow_and_section_are_uppercased_labels():
    assert "text-transform:uppercase" in cfa_style.eyebrow("Exam readiness")
    assert "text-transform:uppercase" in cfa_style.section("Honest scores")


# --------------------------------------------------------------------------
# Palette parity — the F5 invariant: the card :root mirrors the Python tokens.
# --------------------------------------------------------------------------


def _card_root_tokens() -> dict[str, str]:
    css = open(CARD_CSS, encoding="utf-8").read()
    block = re.search(r":root\s*\{([^}]*)\}", css)
    assert block, "the card stylesheet must expose a :root token block"
    out = {}
    for name, val in re.findall(
        r"(--cfa-[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", block.group(1)
    ):
        out[name] = val.lower()
    return out


def test_card_root_mirrors_python_tokens():
    root = _card_root_tokens()
    expected = {
        "--cfa-ink": cfa_style.TOKENS["ink"],
        "--cfa-muted": cfa_style.TOKENS["muted"],
        "--cfa-line": cfa_style.TOKENS["line"],
        "--cfa-surface": cfa_style.TOKENS["surface"],
        "--cfa-primary": cfa_style.TOKENS["primary"],
        "--cfa-primary-soft": cfa_style.TOKENS["primary_soft"],
        "--cfa-primary-hover": cfa_style.TOKENS["primary_hover"],
        "--cfa-pass": cfa_style.TOKENS["pass"],
        "--cfa-fail": cfa_style.TOKENS["fail"],
        "--cfa-accent": cfa_style.TOKENS["accent"],
        "--cfa-accent-soft": cfa_style.TOKENS["accent_soft"],
    }
    for var, py_hex in expected.items():
        assert root.get(var) == py_hex.lower(), (
            f"{var}: card={root.get(var)} py={py_hex}"
        )


def test_card_no_longer_uses_the_old_ad_hoc_blue():
    # The pre-F5 card used a one-off #3b6fe0 blue; F5 unifies it to the navy
    # primary. Guard against the old literal creeping back into styled surfaces.
    css = open(CARD_CSS, encoding="utf-8").read()
    assert "#3b6fe0" not in css


# --------------------------------------------------------------------------
# The real dialogs adopt the shared chrome.
# --------------------------------------------------------------------------


@pytest.fixture
def col(tmp_path):
    from anki.collection import Collection

    c = Collection(str(tmp_path / "f5.anki2"))
    yield c
    c.close()


def _make_mw(col):
    from aqt.qt import QWidget

    class _MW(QWidget):
        def __init__(self):
            super().__init__()
            self.col = col

        def reset(self):
            pass

        def moveToState(self, s):
            pass

    return _MW()


def test_exam_readiness_dialog_applies_shared_style(col):
    from aqt import cfa as aqt_cfa
    from aqt.qt import QApplication

    app = QApplication.instance() or QApplication(["test"])
    assert app is not None
    aqt_cfa.tooltip = lambda *a, **k: None  # type: ignore[assignment]
    deck = col.decks.get_current_id()
    mw = _make_mw(col)  # keep a reference so the parent isn't GC'd
    dlg = aqt_cfa.ExamReadinessDialog(mw, deck)  # type: ignore[arg-type]
    try:
        assert cfa_style.PRIMARY in dlg.styleSheet()
        assert "QTableWidget" in dlg.styleSheet()
    finally:
        dlg.close()


def test_deadline_dialog_applies_shared_style(col):
    from aqt import cfa as aqt_cfa
    from aqt.qt import QApplication

    app = QApplication.instance() or QApplication(["test"])
    assert app is not None
    aqt_cfa.tooltip = lambda *a, **k: None  # type: ignore[assignment]
    mw = _make_mw(col)  # keep a reference so the parent isn't GC'd
    dlg = aqt_cfa.DeadlineDialog(mw)  # type: ignore[arg-type]
    try:
        assert cfa_style.PRIMARY in dlg.styleSheet()
    finally:
        dlg.close()
