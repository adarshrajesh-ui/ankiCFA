# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Regression guard for the Phase-B ethics AI-grade *provenance* fix.

The objective requires the ethics grade to be attributed honestly at all times:
"say ai failed if that call failed, or if the case turned off then say
deterministic". Before this fix the two ethics card templates were both wrong
and inconsistent:

  * ``front.html`` stayed SILENT when AI grading was toggled off (``ai_off``),
    so the user could not tell whether the shown grade came from the LLM or the
    offline rule-based grader.
  * ``passage_front.html`` stayed silent on BOTH the off-state AND a genuine AI
    failure — it only ever rendered a block ``source === "ai"``.

The fix makes ``renderAiGrade`` in BOTH templates render three explicit states:
  1. ``source === "ai"``        → the "AI feedback" block (unchanged)
  2. ``error === "ai_off"``     → a calm "Deterministic" (AI-off) provenance line
  3. any other error           → an "AI failed" warning naming the reason

This stdlib test locks that contract so it cannot silently revert. It parses the
template + CSS source (no browser) — presentation-only, so the byte-mirrored JS
graders (``test_highlight.py`` / ``test_passages.py``) are untouched.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")
FRONT = os.path.join(TEMPLATES, "front.html")
PASSAGE_FRONT = os.path.join(TEMPLATES, "passage_front.html")
CSS = os.path.join(TEMPLATES, "style.css")

# Both ethics card templates render the semantic AI grade + its provenance.
_GRADING_TEMPLATES = (FRONT, PASSAGE_FRONT)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_both_templates_say_deterministic_when_ai_is_off():
    """When AI grading is OFF (``ai_off``) each card explicitly says the grade
    is the offline deterministic one — never stays silent."""
    for path in _GRADING_TEMPLATES:
        src = _read(path)
        assert 'err === "ai_off" || !err' in src, path
        assert ">Deterministic<" in src, path
        assert "AI grading is off" in src, path
        assert "is-off" in src, path


def test_both_templates_say_ai_failed_on_a_real_failure():
    """When an AI call WAS attempted and failed each card says so with a reason
    — distinct from the intentional off-state."""
    for path in _GRADING_TEMPLATES:
        src = _read(path)
        assert ">AI failed<" in src, path
        assert "AI grading failed" in src, path
        assert "is-warn" in src, path
        # the reason map covers the concrete failure codes the bridge emits
        for reason in ("no_api_key", "unparseable_response", "llm_client_unavailable"):
            assert reason in src, (path, reason)


def test_old_silent_off_state_is_gone():
    """The two silent-on-off patterns must not come back."""
    front = _read(FRONT)
    # old front.html guard that suppressed the off-state
    assert 'if (err && err !== "ai_off")' not in front
    passage = _read(PASSAGE_FRONT)
    # old passage_front.html guard that suppressed BOTH off + failure
    assert '!resp || resp.source !== "ai") return' not in passage


def test_mobile_fetch_failure_is_reported_not_swallowed():
    """front.html's Android proxy path no longer swallows a failed fetch —
    it renders an honest 'AI failed' provenance instead of a bare catch."""
    front = _read(FRONT)
    assert "proxy_unreachable" in front
    # the empty ``.catch(function () {});`` swallow is gone
    assert ".catch(function () {});" not in front


def test_css_has_distinct_off_and_warn_provenance_styles():
    """The off-state reads calm/muted; the failure reads as a warn wash — the
    two are visually distinct from each other and from the AI-graded box."""
    css = _read(CSS)
    assert ".cfa-ai.is-off" in css
    assert ".cfa-ai.is-warn" in css
    assert ".cfa-ai-badge.is-off" in css
    assert ".cfa-ai-badge.is-warn" in css
    # night-mode parity for both states
    assert ".nightMode .cfa-ai.is-off" in css
    assert ".nightMode .cfa-ai.is-warn" in css
