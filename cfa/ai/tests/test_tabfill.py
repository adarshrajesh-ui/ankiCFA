# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Shared bidirectional tab-fill logic — direction inference + prompt selection.

Pure/deterministic (no network). Guards the "conditional" both desktop and the
mobile proxy rely on: generate the empty side from the filled one.
"""

from __future__ import annotations

from cfa.ai.tabfill import build_messages, infer_target


def test_infer_target_front_to_back():
    assert infer_target("What is front-running?", "") == "back"
    assert infer_target("Q", "   ") == "back"


def test_infer_target_back_to_front():
    assert infer_target("", "Trading ahead of client orders.") == "front"
    assert infer_target("  ", "A") == "front"


def test_infer_target_none_when_both_filled_or_empty():
    assert infer_target("Q", "A") is None
    assert infer_target("", "") is None
    assert infer_target("   ", "   ") is None


def test_build_messages_back_prompts_for_answer():
    system, user = build_messages("What is duration?", "back", "Basic")
    assert "ANSWER" in system
    assert "Write the BACK" in user
    assert "What is duration?" in user


def test_build_messages_front_prompts_for_question():
    system, user = build_messages("Duration measures interest-rate sensitivity.", "front")
    assert "QUESTION" in system
    assert "Write the FRONT" in user
