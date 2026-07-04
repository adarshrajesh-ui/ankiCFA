# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Shared, bidirectional tab-fill logic: which side to generate + the prompts.

Used by BOTH the desktop editor (``qt/aqt/cfa_tab_fill.py``, local key) and the
mobile AI proxy (``tools/cfa/ai_proxy.py``), so front<->back generation behaves
identically on desktop and phone.

The rule ("conditional"): press Tab / the AI-Fill button and
  * FRONT has text, BACK empty  -> generate the BACK (answer from the question)
  * BACK has text, FRONT empty   -> generate the FRONT (question from the answer)
  * both filled / both empty      -> nothing to do (Tab navigates normally)
"""

from __future__ import annotations

from typing import Optional

# Generate the answer given the question.
_BACK_SYSTEM = (
    "You are a CFA charterholder and Level II exam tutor writing the ANSWER "
    "side (back) of a study flashcard. Given the FRONT (question/prompt), write "
    "a concise, exam-accurate back a candidate can learn from: answer the front "
    "directly; be correct and specific (name the Standard, formula, or "
    "definition where relevant); 1-4 short sentences or a tight bullet list. "
    "Reply with ONLY the answer text — no preamble, no 'Answer:', no quotes."
)

# Generate the question given the answer.
_FRONT_SYSTEM = (
    "You are a CFA charterholder and Level II exam tutor writing the QUESTION "
    "side (front) of a study flashcard. Given the BACK (the answer/fact), write "
    "ONE clear, specific question or prompt whose correct answer is exactly that "
    "back — exam-relevant for CFA Level II, self-contained, unambiguous. Reply "
    "with ONLY the question — no preamble, no answer, no quotes."
)


def infer_target(front: str, back: str) -> Optional[str]:
    """Return which side to generate: ``"back"`` when only the front has text,
    ``"front"`` when only the back has text, else ``None`` (both filled or both
    empty — nothing to generate)."""
    f = (front or "").strip()
    b = (back or "").strip()
    if f and not b:
        return "back"
    if b and not f:
        return "front"
    return None


def build_messages(
    source_text: str,
    target: str,
    notetype_name: str = "",
) -> tuple[str, str]:
    """(system, user) prompt to generate ``target`` ("back"|"front") from
    ``source_text`` (the content of the other, filled side)."""
    source_text = (source_text or "").strip()
    nt = f" (note type: {notetype_name})" if notetype_name else ""
    if target == "front":
        system = _FRONT_SYSTEM
        user = f"BACK (the answer){nt}:\n{source_text}\n\nWrite the FRONT (question) only."
    else:
        system = _BACK_SYSTEM
        user = f"FRONT (the question/prompt){nt}:\n{source_text}\n\nWrite the BACK (answer) only."
    return system, user
