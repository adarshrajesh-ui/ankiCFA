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


def test_both_templates_render_the_per_highlight_critique():
    """Both templates render the per-highlight critique (``per_learner_span``) in the AI block —
    one verdict per phrase the learner ACTUALLY highlighted (decisive / too-broad / partial /
    off-target), quoting their own words. This is the payoff of the AI-grading rework and is
    additive to the existing per-gold-span list, provenance badges, and needed-evidence block."""
    for path in _GRADING_TEMPLATES:
        src = _read(path)
        # the render reads the new field and builds a dedicated block, escaping each string
        assert "resp.per_learner_span" in src, path
        assert "cfa-ai-perhighlight" in src, path
        assert "cfa-pls-" in src, path
        assert "Your highlights, one by one" in src, path
        # the four targeted assessments the learner sees, keyed off resp.per_learner_span[i].assessment
        for label in ("Decisive", "Too broad", "Partial", "Off-target"):
            assert label in src, (path, label)
        # the learner's own words are quoted (esc()) and the critique is additive — the existing
        # per-gold-span list (per_span) still renders too
        assert "esc(pQuote)" in src, path
        assert "resp.per_span" in src, path


def test_old_silent_off_state_is_gone():
    """The two silent-on-off patterns must not come back."""
    front = _read(FRONT)
    # old front.html guard that suppressed the off-state
    assert 'if (err && err !== "ai_off")' not in front
    passage = _read(PASSAGE_FRONT)
    # old passage_front.html guard that suppressed BOTH off + failure
    assert '!resp || resp.source !== "ai") return' not in passage


def test_desktop_pycmd_json_string_is_parsed_before_rendering():
    """Desktop pycmd returns a JSON string; the templates must parse it before
    reading ``resp.source`` or the real AI result is silently treated as
    deterministic/off."""
    for path in _GRADING_TEMPLATES:
        src = _read(path)
        parse_at = src.index("return JSON.parse(resp);")
        source_at = src.index('if (resp.source !== "ai")')
        assert 'function normaliseAiGradeResponse(resp)' in src, path
        assert 'typeof resp === "string"' in src, path
        assert parse_at < source_at, path


def test_mobile_fetch_failure_is_reported_not_swallowed():
    """Android proxy failures render honest 'AI failed' provenance."""
    for path in _GRADING_TEMPLATES:
        src = _read(path)
        assert "proxy_unreachable" in src, path
        # the empty ``.catch(function () {});`` swallow is gone
        assert ".catch(function () {});" not in src, path


def test_mobile_grade_honours_the_synced_ai_toggle():
    """On the phone the ethics card must NOT hit the AI proxy when the synced
    AI-grading toggle is off — it shows the honest "Deterministic" state, exactly
    like the desktop pycmd bridge (error="ai_off"). AnkiDroid injects
    ``window.CFA_AI_GRADING_ENABLED`` from col.conf; an explicit ``false`` skips
    the fetch. (undefined => on, so older builds keep working.)"""
    for path in _GRADING_TEMPLATES:
        src = _read(path)
        # the toggle gate exists, guards the Android fetch, and is checked strictly
        assert "window.CFA_AI_GRADING_ENABLED === false" in src, path
        # when off it renders the deterministic (ai_off) state, not a proxy call
        assert 'renderAiGrade({ source: "fallback", error: "ai_off" });' in src, path
        # the gate is checked before any platform branch or proxy fetch
        gate_at = src.index("window.CFA_AI_GRADING_ENABLED === false")
        fetch_at = src.index('fetch(proxyUrl + "/cfa/grade"')
        assert gate_at < fetch_at


def test_mobile_grade_uses_injected_proxy_config_without_pycmd_gate():
    """Android grading must use configured proxy URL/token before pycmd guard."""
    for path in _GRADING_TEMPLATES:
        src = _read(path)
        android_at = src.index('if (/android/i.test(navigator.userAgent || ""))')
        android_proxy_at = src.index('tryProxyGrade(payload, renderAiGrade')
        pycmd_guard_at = src.index('if (typeof pycmd === "undefined")')
        assert android_at < android_proxy_at < pycmd_guard_at
        assert 'window.CFA_AI_PROXY_URL || defaultProxyUrl()' in src, path
        assert '"http://10.0.2.2:27702"' in src, path
        assert 'window.CFA_AI_PROXY_TOKEN || "cfa-ai-proxy"' in src, path
        assert '"Authorization": "Bearer " + proxyToken' in src, path


def test_desktop_grade_retries_running_local_proxy_after_bridge_fallback():
    """Desktop pycmd can lack OPENAI_API_KEY even when the standalone proxy is
    healthy. A non-AI bridge response must retry localhost before rendering the
    deterministic fallback."""
    for path in _GRADING_TEMPLATES:
        src = _read(path)
        assert '"http://127.0.0.1:27702"' in src, path
        assert "function shouldRetryProxy(resp)" in src, path
        assert "tryProxyGrade(payload, renderAiGrade" in src, path
        bridge_at = src.index('pycmd("cfaGradeEthics:"')
        retry_at = src.index("shouldRetryProxy(resp)")
        proxy_at = src.index("tryProxyGrade(payload, renderAiGrade", retry_at)
        assert bridge_at < retry_at < proxy_at


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
