# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Presentation guards for Ethics cards in phone review mode.

These tests read the templates/CSS source directly. The selection and grading
logic remains covered by the shared JS/Python parity tests.
"""

from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")
CSS = os.path.join(TEMPLATES, "style.css")
PAIR_FRONT = os.path.join(TEMPLATES, "front.html")
PASSAGE_FRONT = os.path.join(TEMPLATES, "passage_front.html")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_ethics_css_has_phone_layout_for_pair_and_passage_fronts() -> None:
    css = _read(CSS)
    assert "Phone reviewer layout" in css
    assert "@media (max-width: 640px)" in css
    assert "env(safe-area-inset-right, 0px)" in css
    assert "env(safe-area-inset-left, 0px)" in css
    assert ".cfa-cases {\n    grid-template-columns: 1fr;" in css
    assert ".cfa-case,\n  .cfa-passage-wrap" in css
    assert ".cfa-judge,\n  .cfa-verdict-btns" in css
    assert "min-height: 48px;" in css
    assert "white-space: normal;" in css
    assert "touch-action: pan-y;" in css
    assert "touch-action: manipulation;" in css


def test_ethics_css_keeps_reveal_ai_and_record_controls_readable_on_phone() -> None:
    css = _read(CSS)
    assert ".cfa-reveal,\n  .cfa-commit-reveal,\n  .cfa-ai" in css
    assert "padding: 16px 14px;" in css
    assert "#cfa-check,\n  #cfa-record-btn {\n    width: 100%;" in css
    assert ".cfa-span-controls {\n    display: grid;" in css
    assert ".cfa-commit {\n    max-width: none;" in css


def test_ethics_css_has_desktop_webview_fit_guards() -> None:
    css = _read(CSS)
    assert ".cfa-pair,\n.cfa-case,\n.cfa-passage-wrap,\n.cfa-reveal,\n.cfa-commit,\n.cfa-commit-reveal,\n.cfa-ai" in css
    assert "box-sizing: border-box;" in css
    assert ".cfa-pair {\n  width: 100%;" in css
    assert ".cfa-commit { width: 100%; max-width: 720px;" in css
    assert "@media (max-width: 760px)" in css
    assert ".cfa-verdict-btns {\n    display: grid;" in css
    assert "overflow-wrap: anywhere;" in css


def test_ethics_fronts_capture_touch_pointer_drags() -> None:
    for path in (PAIR_FRONT, PASSAGE_FRONT):
        src = _read(path)
        assert "setPointerCapture" in src, path
        assert "releasePointerCapture" in src, path
        assert "ev.pointerId != null" in src, path
