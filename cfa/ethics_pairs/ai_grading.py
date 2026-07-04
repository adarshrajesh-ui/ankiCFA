# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F2 — semantic AI grading of the one-passage ethics highlights.

At review time the learner picks Ethical/Unethical and highlights the evidence
span(s). F1 grades that highlight deterministically by token-index overlap
(``ethics_scoring.grade_passage_attempt``). That is exact but brittle: a learner
who highlights *"sold the client's holdings"* when the gold span is *"sells the
company out of her clients' portfolios"* is semantically right but scores
``partial`` because the token runs differ.

F2 adds a **semantic** grade on top. It sends ``{passage, verdict, learner
spans, gold spans, rationale}`` through :mod:`cfa.ai.llm_client` and asks the
model to judge, WITH TOLERANCE, whether the learner's spans cover each gold
piece of evidence — returning a grade plus a short explanation of what was
nailed and what was missed.

Hard rule from the objective — **every AI feature works fully with AI OFF**:

    * If ``OPENAI_API_KEY`` is absent, the LLM call, a network error, the cost
      cap, or an unparseable reply all mean :func:`grade_semantic` returns the
      *exact* F1 deterministic grade with ``source == "fallback"``.
    * :func:`grade_semantic` NEVER raises. The API key is never placed in the
      prompt or any returned value.

This module is PURE (no ``anki`` import) so it is unit-testable with a mocked
client. ``qt/aqt/cfa_ethics_ai.py`` is the thin desktop pycmd bridge that calls
it; the card template JS keeps its own deterministic grade so mobile / AI-off
still works instantly, and augments the reveal with the AI explanation when the
bridge returns one.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Optional

from ethics_scoring import (
    PassageAttempt,
    find_gold_spans,
    grade_passage_attempt,
)

GRADES = ("correct", "somewhat", "partial", "wrong")

_SYSTEM_PROMPT = (
    "You are a CFA Institute Code and Standards tutor grading AND coaching one "
    "learner. They read a passage, judged the conduct Ethical or Unethical, and "
    "highlighted the phrase(s) they believe are the evidence. You get the "
    "passage, their verdict, the correct verdict, their highlighted phrases, and "
    "the authored GOLD evidence spans (each with a rationale). Grade the "
    "highlight SEMANTICALLY (meaning, not exact wording) and give feedback that "
    "is PERSONAL to THIS learner's actual answer — the whole point is that AI "
    "grading is more useful than an exact-match check.\n\n"
    "Tolerance rules (the error margin):\n"
    "- A gold span counts as MATCHED if any learner phrase refers to the same "
    "underlying fact/evidence — different words, tense, paraphrase, or slightly "
    "different boundaries all count. Reward the right idea; never require exact "
    "token overlap.\n"
    "- Extra learner phrases that are not evidence are tolerated unless they "
    "dominate (many irrelevant phrases -> at best 'somewhat').\n\n"
    "Highlight grade (about the spans ONLY, independent of the verdict):\n"
    "- 'correct'  : every gold span is matched and the selection is focused.\n"
    "- 'somewhat' : every gold span is matched but also lots of irrelevant text.\n"
    "- 'partial'  : at least one but not all gold spans are matched.\n"
    "- 'wrong'    : no gold span is matched.\n\n"
    "Feedback rules — make it TAILORED, not generic:\n"
    "- Quote or reference the learner's OWN highlighted words when praising or "
    "correcting them.\n"
    "- Name the specific CFA Standard at issue and, in one plain-language "
    "sentence, WHY the gold evidence is decisive here.\n"
    "- If their verdict was wrong, explain the misread; if right but the "
    "highlight was off, say what stronger evidence to point to.\n"
    "- The study tip must be concrete and specific to THIS Standard/skill.\n\n"
    "Reply with ONLY a JSON object, no prose, no code fence:\n"
    '{"verdict_correct": <true|false>, '
    '"highlight_grade": "correct|somewhat|partial|wrong", '
    '"confidence": <0.0-1.0>, '
    '"standard": "<the governing CFA Standard code and name you identify>", '
    '"explanation": "<=40 words: what evidence was nailed and what was missed", '
    '"coaching": "<=70 words: personal feedback that references the learner\'s own '
    "verdict + highlighted words and the Standard; this is the payoff for AI grading>\", "
    '"study_tip": "<=25 words: one concrete next step for this Standard/skill", '
    '"spans": [{"phrase": "<gold phrase>", "matched": <true|false>, '
    '"note": "<why THIS phrase is (or is not) the decisive evidence>"}]}'
)


def _clean_grade(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip().lower() in GRADES:
        return value.strip().lower()
    return default


def _build_user_prompt(
    passage: str,
    answer_verdict: str,
    judged_verdict: str,
    gold_spans: Sequence[dict],
    learner_spans: Sequence[str],
) -> str:
    gold_lines = "\n".join(
        f'  {i + 1}. "{g.get("phrase", "")}" — {g.get("rationale", "")}'
        for i, g in enumerate(gold_spans)
    )
    learner_lines = (
        "\n".join(f'  - "{p}"' for p in learner_spans if str(p).strip())
        or "  (the learner highlighted nothing)"
    )
    return (
        f"PASSAGE:\n{passage}\n\n"
        f"CORRECT VERDICT: {answer_verdict}\n"
        f"LEARNER'S VERDICT: {judged_verdict}\n\n"
        f"GOLD EVIDENCE SPANS:\n{gold_lines}\n\n"
        f"LEARNER'S HIGHLIGHTED PHRASES:\n{learner_lines}\n\n"
        "Grade now. Reply with ONLY the JSON object."
    )


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort parse of the first balanced JSON object in ``text``."""
    if not text:
        return None
    stripped = text.strip()
    # tolerate ```json ... ``` fences
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    start = stripped.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(stripped)):
        c = stripped[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(stripped[start : i + 1])
                    return obj if isinstance(obj, dict) else None
                except (ValueError, TypeError):
                    return None
    return None


def _selection_from_spans(passage: str, learner_spans: Sequence[str]) -> list[int]:
    """Resolve the learner's highlighted phrases back to a union of token indices."""
    runs = find_gold_spans(passage, [p for p in learner_spans if str(p).strip()])
    out: list[int] = []
    for run in runs:
        out.extend(run)
    return out


def grade_fallback(
    passage: str,
    answer_verdict: str,
    judged_verdict: str,
    gold_spans: Sequence[dict],
    learner_spans: Sequence[str] = (),
    selection_indices: Optional[Sequence[int]] = None,
    error: str = "ai_off",
    *,
    item_id: str = "",
    standard: str = "",
) -> dict:
    """The deterministic F1 grade, shaped like :func:`grade_semantic`'s result.

    This is the AI-OFF fallback. It is a pure re-projection of
    ``grade_passage_attempt`` — no LLM, no network — so it always succeeds.

    ``item_id`` and ``standard`` are echoed straight back into the result (they are
    provenance the card supplies) so the UI can render the named governing Standard
    even on the fallback path (``"Graded by AI"`` only when ``source == "ai"``).
    """
    phrases = [g.get("phrase", "") for g in gold_spans]
    gold_runs = find_gold_spans(passage, phrases)
    if selection_indices is None:
        selection_indices = _selection_from_spans(passage, learner_spans)
    res = grade_passage_attempt(
        PassageAttempt(
            judged_verdict, answer_verdict, list(selection_indices), gold_runs
        )
    )
    per_span = [
        {
            "phrase": phrases[i],
            "matched": bool(res["spans"]["per_span"][i]),
            "note": gold_spans[i].get("rationale", "") if i < len(gold_spans) else "",
        }
        for i in range(len(phrases))
    ]
    found = res["spans"]["found"]
    total = res["spans"]["total"]
    explanation = (
        f"Matched {found} of {total} evidence span(s) by exact-phrase overlap "
        "(deterministic AI-off grade)."
    )
    # Terse deterministic feedback — deliberately thinner than the AI path so the
    # value of enabling AI grading (personal coaching + a targeted tip) is clear.
    std_txt = f" (Standard {standard})" if standard else ""
    coaching = (
        "Deterministic grade by exact-phrase overlap. Turn on AI grading for "
        f"feedback tailored to your verdict and highlight{std_txt}."
    )
    study_tip = f"Review the evidence for Standard {standard}." if standard else ""
    return {
        "ok": False,
        "source": "fallback",
        "grade": res["highlight"],
        "verdict_correct": res["verdict_correct"],
        "correct": res["correct"],
        "explanation": explanation,
        "coaching": coaching,
        "study_tip": study_tip,
        "confidence": None,
        "per_span": per_span,
        "error": error,
        "model": None,
        "item_id": item_id,
        "standard": standard,
    }


def grade_semantic(
    passage: str,
    answer_verdict: str,
    judged_verdict: str,
    gold_spans: Sequence[dict],
    learner_spans: Sequence[str] = (),
    *,
    selection_indices: Optional[Sequence[int]] = None,
    max_tokens: int = 400,
    timeout: float = 30.0,
    complete_fn=None,
    item_id: str = "",
    standard: str = "",
) -> dict:
    """Grade a one-passage / minimal-pair ethics attempt with semantic tolerance, or fall back.

    ``learner_spans`` are the TEXT of the phrases the learner highlighted;
    ``gold_spans`` are the authored ``{phrase, rationale}`` dicts. On any
    problem (AI off, network error, cost cap, unparseable reply) this returns
    the deterministic F1 grade with ``source == "fallback"``. Never raises.

    ``item_id`` and ``standard`` are PROVENANCE the card supplies and are echoed
    into the result on BOTH paths, so the UI can render the named governing
    Standard (e.g. "Graded by AI · II(A) Material Nonpublic Information"). The key
    is NEVER placed in the prompt or any returned value.

    ``complete_fn`` is an injection point for tests; production passes ``None``
    and the shared :mod:`cfa.ai.llm_client` is used.
    """
    answer_verdict = (answer_verdict or "").strip().lower()
    judged_verdict = (judged_verdict or "").strip().lower()
    verdict_correct = judged_verdict == answer_verdict

    if complete_fn is None:
        try:
            from cfa.ai.llm_client import complete as complete_fn  # type: ignore
        except Exception:
            return grade_fallback(
                passage,
                answer_verdict,
                judged_verdict,
                gold_spans,
                learner_spans,
                selection_indices,
                error="llm_client_unavailable",
                item_id=item_id,
                standard=standard,
            )

    system = _SYSTEM_PROMPT
    user = _build_user_prompt(
        passage, answer_verdict, judged_verdict, gold_spans, learner_spans
    )
    result = complete_fn(
        system=system,
        user=user,
        max_tokens=max_tokens,
        temperature=0.0,
        timeout=timeout,
        purpose="grade_ethics_highlight",
    )
    if not result or not result.get("ok"):
        return grade_fallback(
            passage,
            answer_verdict,
            judged_verdict,
            gold_spans,
            learner_spans,
            selection_indices,
            error=(result or {}).get("error", "ai_unavailable"),
            item_id=item_id,
            standard=standard,
        )

    parsed = _extract_json(result.get("text", ""))
    if parsed is None:
        return grade_fallback(
            passage,
            answer_verdict,
            judged_verdict,
            gold_spans,
            learner_spans,
            selection_indices,
            error="unparseable_response",
            item_id=item_id,
            standard=standard,
        )

    grade = _clean_grade(parsed.get("highlight_grade"), "wrong")
    # Trust the deterministic verdict check over the model's self-report; the
    # verdict is a simple string equality and must not drift.
    ai_verdict_correct = verdict_correct
    correct = ai_verdict_correct and grade == "correct"

    phrases = [g.get("phrase", "") for g in gold_spans]
    span_reports = parsed.get("spans")
    per_span: list[dict] = []
    if isinstance(span_reports, list) and span_reports:
        # align model spans to gold phrases by order, padding/truncating safely
        for i, phrase in enumerate(phrases):
            src = span_reports[i] if i < len(span_reports) else {}
            src = src if isinstance(src, dict) else {}
            per_span.append(
                {
                    "phrase": phrase,
                    "matched": bool(src.get("matched", False)),
                    "note": str(src.get("note", "")),
                }
            )
    else:
        per_span = [{"phrase": p, "matched": False, "note": ""} for p in phrases]

    explanation = str(parsed.get("explanation", "")).strip() or "Graded by AI."
    coaching = str(parsed.get("coaching", "")).strip()
    study_tip = str(parsed.get("study_tip", "")).strip()
    # Model may refine the named Standard; fall back to the card-supplied one.
    ai_standard = str(parsed.get("standard", "")).strip() or standard
    try:
        confidence = float(parsed.get("confidence"))
    except (TypeError, ValueError):
        confidence = None
    return {
        "ok": True,
        "source": "ai",
        "grade": grade,
        "verdict_correct": ai_verdict_correct,
        "correct": correct,
        "explanation": explanation,
        "coaching": coaching,
        "study_tip": study_tip,
        "confidence": confidence,
        "per_span": per_span,
        "error": None,
        "model": result.get("model"),
        "item_id": item_id,
        "standard": ai_standard,
    }


__all__ = ["grade_semantic", "grade_fallback", "GRADES"]
