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
    find_gold_indices,
    find_gold_spans,
    grade_passage_attempt,
    span_cap,
    span_tier,
    tokenize,
)

GRADES = ("correct", "somewhat", "partial", "wrong")

# Assessment tiers for an INDIVIDUAL learner highlight (the ``per_learner_span`` critique). These
# describe what the learner ACTUALLY selected so feedback is targeted at each thing they highlighted:
#   - "decisive"   : this is the right, focused evidence.
#   - "excessive"  : right region but too broad (the decisive words are buried in a much wider grab).
#   - "partial"    : captures some of a required span / some decisive words, but not the whole thing.
#   - "irrelevant" : does not help the ethical/unethical case (the wrong piece).
# The model chooses the tier per highlight; the deterministic AI-off path derives it from word overlap.
LEARNER_SPAN_ASSESSMENTS = ("decisive", "excessive", "partial", "irrelevant")

# A highlight that fully covers a gold span but carries more than this many EXTRA (non-decisive) words
# reads as "excessive"; a small boundary margin around the decisive evidence still reads as "decisive".
_FOCUS_SLACK = 3

_SYSTEM_PROMPT = (
    "You are a CFA Institute Code and Standards tutor grading AND coaching one "
    "learner. They read a passage, judged the conduct Ethical or Unethical, and "
    "highlighted the phrase(s) they believe are the evidence. You get the "
    "passage, their verdict, the correct verdict, their highlighted phrases, and "
    "the exact highlight token ranges/coverage when available, "
    "the governing Standard, and the authored GOLD evidence spans (each with a "
    "rationale). Grade the highlight SEMANTICALLY (meaning, not exact wording) "
    "and give feedback that "
    "is PERSONAL to THIS learner's actual answer — the whole point is that AI "
    "grading is more useful than an exact-match check.\n\n"
    "Tolerance rules (the error margin):\n"
    "- A gold span counts as MATCHED if any learner phrase refers to the same "
    "underlying fact/evidence — different words, tense, paraphrase, or slightly "
    "different boundaries all count. Reward the right idea; never require exact "
    "token overlap.\n"
    "- Extra learner phrases that are not evidence are tolerated in proportion: "
    "a few boundary words around the right evidence can still be correct; about "
    "10 extra words beyond the decisive evidence should usually be 'somewhat'; "
    "highlighting a whole paragraph or most of the passage is poor evidence "
    "selection and must not be 'correct'.\n\n"
    "Highlight grade (about the spans ONLY, independent of the verdict):\n"
    "- 'correct'  : every gold span is matched and the selection is focused.\n"
    "- 'somewhat' : every gold span is matched but also lots of irrelevant text.\n"
    "- 'partial'  : at least one but not all gold spans are matched.\n"
    "- 'wrong'    : no gold span is matched.\n\n"
    "Feedback rules — make it TAILORED, not generic:\n"
    "- Quote or reference the learner's OWN highlighted words when praising or "
    "correcting them.\n"
    "- Cite the governing CFA Standard. If the card supplies one, use it; "
    "otherwise infer the best Standard from the facts and gold rationales.\n"
    "- Infer what the learner was likely gunning for from their highlight(s), "
    "then say whether that reasoning/evidence was right, wrong, overbroad, "
    "partially relevant, or missing.\n"
    "- Explain in natural CFA tutor language why the correct verdict is correct "
    "and why the decisive evidence matters. Do not only say the answer is right.\n"
    "- If their verdict was wrong, explain the misread; if right but the "
    "highlight was off, say what stronger evidence to point to.\n"
    "- Tell them the exact evidence that should have been highlighted.\n"
    "- The study tip must be concrete and specific to THIS Standard/skill.\n\n"
    "PER-HIGHLIGHT CRITIQUE — the MOST IMPORTANT part. The feedback must be "
    "TARGETED AT WHAT THE LEARNER ACTUALLY HIGHLIGHTED:\n"
    "- Address EACH learner highlight individually, in order, QUOTING the "
    "learner's OWN words. The learner may make SEVERAL highlights (several "
    "phrases, several lines) — critique every one, and support multiple.\n"
    "- Classify each highlight as exactly one of: 'decisive' (this IS the right, "
    "focused evidence), 'excessive' (right region but TOO BROAD — they grabbed "
    "much more than the small decisive piece), 'partial' (captures some of a "
    "required span or some of the decisive words, but not the whole thing), or "
    "'irrelevant' (does NOT help the ethical/unethical case — the wrong piece).\n"
    "- When a highlight is not the best evidence, say WHY: they highlighted too "
    "much when a small piece would do, highlighted the wrong piece, or missed one "
    "of the required spans.\n"
    "- Partial-credit nuance to apply: capturing the decisive words INSIDE a "
    "larger highlight is 'excessive' (right idea, over-selected) and usually makes "
    "the overall highlight_grade 'somewhat'; capturing 2 of 3 decisive words is "
    "'partial' and the grade is 'somewhat'/'partial'; missing a required span or "
    "highlighting the wrong piece is 'partial'/'wrong'.\n"
    "- The deterministic per-highlight and per-gold-span word-coverage numbers in "
    "the user message are GUIDANCE to ground these calls — YOU still decide each "
    "grade; do not just echo them.\n\n"
    "Reply with ONLY a JSON object, no prose, no code fence:\n"
    '{"verdict_correct": <true|false>, '
    '"highlight_grade": "correct|somewhat|partial|wrong", '
    '"confidence": <0.0-1.0>, '
    '"standard": "<the governing CFA Standard code and name you identify>", '
    '"learner_intent": "<what the learner likely noticed or was trying to prove>", '
    '"evidence_precision": "precise|mostly_precise|overbroad|partial|missing|wrong_case", '
    '"needed_evidence": ["<exact decisive evidence phrase>", "..."], '
    '"explanation": "<what evidence was nailed and what was missed>", '
    '"coaching": "<personal feedback that references the learner\'s own '
    "verdict + highlighted words and the Standard; this is the payoff for AI grading>\", "
    '"study_tip": "<one concrete next step for this Standard/skill>", '
    '"per_learner_span": [{"quote": "<the learner\'s OWN highlighted words>", '
    '"assessment": "decisive|excessive|partial|irrelevant", '
    '"note": "<why THIS highlight is or is not the best evidence — too broad, '
    'wrong piece, or missing part of a required span>"}], '
    '"spans": [{"phrase": "<gold phrase>", "matched": <true|false>, '
    '"note": "<why THIS phrase is (or is not) the decisive evidence>"}]}'
)


def _clean_grade(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip().lower() in GRADES:
        return value.strip().lower()
    return default


def _clean_precision(value: object, default: str) -> str:
    allowed = {
        "precise",
        "mostly_precise",
        "overbroad",
        "partial",
        "missing",
        "wrong_case",
    }
    if isinstance(value, str):
        cleaned = value.strip().lower().replace("-", "_").replace(" ", "_")
        if cleaned in allowed:
            return cleaned
    return default


def _normalise_learner_highlights(
    learner_spans: Sequence[str],
    learner_highlights: object = None,
) -> list[dict]:
    """Return structured highlight rows with text plus optional token bounds."""
    out: list[dict] = []
    if isinstance(learner_highlights, list):
        for item in learner_highlights:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or item.get("phrase") or "").strip()
            if not text:
                continue
            row: dict[str, object] = {"text": text}
            for key in ("lo", "hi"):
                try:
                    if item.get(key) is not None:
                        row[key] = int(item.get(key))
                except (TypeError, ValueError):
                    pass
            out.append(row)
    if out:
        return out
    return [{"text": str(p).strip()} for p in learner_spans if str(p).strip()]


def _selection_summary(passage: str, selection_indices: Optional[Sequence[int]]) -> dict:
    total = len(tokenize(passage))
    selected = len(set(int(i) for i in (selection_indices or [])))
    ratio = (selected / total) if total else 0.0
    return {"selected": selected, "total": total, "ratio": ratio}


def _highlight_indices(passage: str, highlight: dict) -> set:
    """Resolve ONE learner highlight to its passage token indices.

    Uses the supplied ``lo``/``hi`` token bounds when present; otherwise locates the highlight text
    inside the passage with the shared tokenizer (mirrors how the card resolves a highlight).
    """
    lo = highlight.get("lo")
    hi = highlight.get("hi")
    if lo is not None and hi is not None:
        try:
            lo_i, hi_i = int(lo), int(hi)
            if hi_i >= lo_i:
                return set(range(lo_i, hi_i + 1))
        except (TypeError, ValueError):
            pass
    return set(find_gold_indices(passage, str(highlight.get("text", ""))))


def _coverage(
    passage: str, gold_spans: Sequence[dict], highlights: Sequence[dict]
) -> tuple[list[dict], list[dict]]:
    """Deterministic per-gold-span AND per-learner-highlight word coverage (prompt GUIDANCE).

    Returns ``(gold_coverage, highlight_coverage)``:

    * ``gold_coverage`` — per authored gold span: how many of its decisive words the learner captured
      (``captured_words`` of ``decisive_words``) plus the tolerant ``tier`` (full/near/none), e.g.
      "captured 2 of 3 decisive words".
    * ``highlight_coverage`` — per learner highlight: its ``width`` in words, how many are ``decisive``
      (overlap a gold span) vs ``extra``, which gold spans it ``touches`` / ``fully_covers``, e.g.
      "3 decisive words inside a 6-word highlight".

    Reuses ``ethics_scoring.span_tier`` for the per-span tiers, keeping the numbers consistent with the
    deterministic AI-off grader.
    """
    phrases = [g.get("phrase", "") for g in gold_spans]
    gold_runs = find_gold_spans(passage, phrases)
    gold_sets = [set(run) for run in gold_runs]
    all_gold: set[int] = set()
    for gs in gold_sets:
        all_gold |= gs

    hl_indices = [_highlight_indices(passage, h) for h in highlights]
    selection: set[int] = set()
    for idxs in hl_indices:
        selection |= idxs

    gold_coverage: list[dict] = []
    for i, gs in enumerate(gold_sets):
        gold_coverage.append(
            {
                "phrase": phrases[i],
                "rationale": (
                    gold_spans[i].get("rationale", "") if i < len(gold_spans) else ""
                ),
                "decisive_words": len(gs),
                "captured_words": len(gs & selection),
                "tier": span_tier(selection, gold_runs[i]),
            }
        )

    highlight_coverage: list[dict] = []
    for h, idxs in zip(highlights, hl_indices):
        touches: list[int] = []
        fully: list[int] = []
        for i, gs in enumerate(gold_sets):
            if gs and (idxs & gs):
                touches.append(i)
                if gs.issubset(idxs):
                    fully.append(i)
        decisive = len(idxs & all_gold)
        highlight_coverage.append(
            {
                "text": str(h.get("text", "")),
                "width": len(idxs),
                "decisive_words": decisive,
                "extra_words": len(idxs) - decisive,
                "touches": touches,
                "fully_covers": fully,
            }
        )
    return gold_coverage, highlight_coverage


def _tier_word(tier: str) -> str:
    return {"full": "fully captured", "near": "partially captured", "none": "missed"}.get(
        tier, tier
    )


def _coverage_guidance(
    gold_coverage: Sequence[dict], highlight_coverage: Sequence[dict]
) -> str:
    """Render the deterministic coverage numbers as prompt GUIDANCE lines (the model still grades)."""
    lines = [
        "PER-HIGHLIGHT COVERAGE (deterministic word overlap — GUIDANCE only; "
        "YOU decide each grade):"
    ]
    if highlight_coverage:
        for i, hc in enumerate(highlight_coverage):
            if hc["width"] == 0:
                where = " (could not be located in the passage)"
            elif not hc["touches"]:
                where = " (overlaps NO gold span — likely irrelevant)"
            elif hc["fully_covers"]:
                where = " (fully covers gold span " + ", ".join(
                    str(t + 1) for t in hc["fully_covers"]
                ) + ")"
            else:
                where = " (overlaps gold span " + ", ".join(
                    str(t + 1) for t in hc["touches"]
                ) + " but not fully)"
            lines.append(
                f'  {i + 1}. "{hc["text"]}": {hc["decisive_words"]} decisive words '
                f'inside a {hc["width"]}-word highlight{where}.'
            )
    else:
        lines.append("  (the learner highlighted nothing)")
    lines.append("")
    lines.append("PER-GOLD-SPAN COVERAGE (deterministic — GUIDANCE only):")
    if gold_coverage:
        for i, gc in enumerate(gold_coverage):
            lines.append(
                f'  {i + 1}. "{gc["phrase"]}": learner captured '
                f'{gc["captured_words"]} of {gc["decisive_words"]} decisive words '
                f'({_tier_word(gc["tier"])}).'
            )
    else:
        lines.append("  (no gold spans supplied)")
    return "\n".join(lines)


def _derive_per_learner_span(highlight_coverage: Sequence[dict]) -> list[dict]:
    """Deterministic per-highlight assessment: the AI-off critique and the AI-path fallback shape.

    One row per learner highlight so ``per_learner_span`` is always stable-shaped, keyed to what the
    learner actually highlighted.
    """
    out: list[dict] = []
    for hc in highlight_coverage:
        width = int(hc.get("width", 0))
        decisive = int(hc.get("decisive_words", 0))
        extra = int(hc.get("extra_words", max(0, width - decisive)))
        fully = list(hc.get("fully_covers", []))
        if width == 0:
            assessment = "irrelevant"
            note = "This highlight could not be located in the passage."
        elif decisive == 0:
            assessment = "irrelevant"
            note = (
                "None of these words are decisive evidence — this highlight does "
                "not help prove the case."
            )
        elif fully:
            if extra <= _FOCUS_SLACK:
                assessment = "decisive"
                note = "Focused on the decisive evidence."
            else:
                assessment = "excessive"
                note = (
                    f"Contains the decisive evidence but is {extra} words too broad "
                    "— a smaller highlight would do."
                )
        else:
            assessment = "partial"
            note = (
                f"Overlaps the evidence ({decisive} of {width} highlighted words are "
                "decisive) but does not capture a whole required span."
            )
        out.append(
            {
                "quote": hc.get("text", ""),
                "assessment": assessment,
                "note": note,
                "decisive_words": decisive,
                "highlight_words": width,
            }
        )
    return out


def _clean_assessment(value: object, default: str) -> str:
    if isinstance(value, str):
        cleaned = value.strip().lower().replace("-", "_").replace(" ", "_")
        synonyms = {
            "overbroad": "excessive",
            "too_broad": "excessive",
            "broad": "excessive",
            "over_selected": "excessive",
            "off_target": "irrelevant",
            "off": "irrelevant",
            "wrong": "irrelevant",
            "wrong_piece": "irrelevant",
            "somewhat": "partial",
            "partially_right": "partial",
            "partial_credit": "partial",
            "correct": "decisive",
            "precise": "decisive",
        }
        cleaned = synonyms.get(cleaned, cleaned)
        if cleaned in LEARNER_SPAN_ASSESSMENTS:
            return cleaned
    return default


def _parse_per_learner_span(
    raw: object, derived: Sequence[dict]
) -> list[dict]:
    """Parse the model's per-highlight critique, aligned by order to the learner's highlights.

    Falls back to the deterministic ``derived`` row when the model omits or malforms an entry, so
    every learner highlight always yields one stable-shaped row.
    """
    raw_list = raw if isinstance(raw, list) else []
    rows: list[dict] = []
    n = max(len(derived), len(raw_list))
    for i in range(n):
        base = dict(derived[i]) if i < len(derived) else {}
        item = raw_list[i] if i < len(raw_list) and isinstance(raw_list[i], dict) else {}
        quote = str(
            item.get("quote")
            or item.get("phrase")
            or item.get("text")
            or base.get("quote", "")
        ).strip()
        assessment = _clean_assessment(
            item.get("assessment"), base.get("assessment", "partial")
        )
        note = str(item.get("note", "")).strip() or base.get("note", "")
        row: dict[str, object] = {"quote": quote, "assessment": assessment, "note": note}
        if "decisive_words" in base:
            row["decisive_words"] = base["decisive_words"]
        if "highlight_words" in base:
            row["highlight_words"] = base["highlight_words"]
        rows.append(row)
    return rows


def _fallback_precision(
    passage: str,
    grade: str,
    gold_spans: Sequence[dict],
    selection_indices: Optional[Sequence[int]],
) -> str:
    summary = _selection_summary(passage, selection_indices)
    selected = int(summary["selected"])
    total = int(summary["total"])
    if selected == 0:
        return "missing"
    phrases = [g.get("phrase", "") for g in gold_spans]
    gold_runs = find_gold_spans(passage, phrases)
    gold_count = len({idx for run in gold_runs for idx in run})
    cap = span_cap(gold_count, len(gold_runs))
    if total and selected / total >= 0.65:
        return "overbroad"
    if selected > cap:
        return "overbroad"
    if grade == "correct":
        return "precise"
    if grade == "somewhat":
        return "mostly_precise"
    if grade == "partial":
        return "partial"
    return "missing"


def _build_user_prompt(
    passage: str,
    answer_verdict: str,
    judged_verdict: str,
    gold_spans: Sequence[dict],
    learner_spans: Sequence[str],
    selection_indices: Optional[Sequence[int]] = None,
    learner_highlights: object = None,
    standard: str = "",
) -> str:
    gold_lines = "\n".join(
        f'  {i + 1}. "{g.get("phrase", "")}" — {g.get("rationale", "")}'
        for i, g in enumerate(gold_spans)
    )
    highlights = _normalise_learner_highlights(learner_spans, learner_highlights)
    learner_lines_parts = []
    for h in highlights:
        bounds = ""
        if h.get("lo") is not None and h.get("hi") is not None:
            bounds = f" (token range {h['lo']}-{h['hi']})"
        learner_lines_parts.append(f'  - "{h["text"]}"{bounds}')
    learner_lines = (
        "\n".join(learner_lines_parts) or "  (the learner highlighted nothing)"
    )
    summary = _selection_summary(passage, selection_indices)
    coverage_line = (
        "HIGHLIGHT COVERAGE: "
        f"{summary['selected']} of {summary['total']} passage tokens "
        f"({summary['ratio']:.0%}). Use this to judge precision/overbreadth.\n"
        if selection_indices is not None
        else "HIGHLIGHT COVERAGE: token ranges not supplied.\n"
    )
    standard_line = (
        f"GOVERNING STANDARD SUPPLIED BY CARD: {standard}\n"
        if str(standard).strip()
        else "GOVERNING STANDARD SUPPLIED BY CARD: (not supplied; infer it)\n"
    )
    gold_coverage, highlight_coverage = _coverage(passage, gold_spans, highlights)
    guidance = _coverage_guidance(gold_coverage, highlight_coverage)
    return (
        f"PASSAGE:\n{passage}\n\n"
        f"{standard_line}"
        f"CORRECT VERDICT: {answer_verdict}\n"
        f"LEARNER'S VERDICT: {judged_verdict}\n\n"
        f"GOLD EVIDENCE SPANS:\n{gold_lines}\n\n"
        f"LEARNER'S HIGHLIGHTED PHRASES:\n{learner_lines}\n"
        f"{coverage_line}\n"
        f"{guidance}\n\n"
        "Now critique EACH learner highlight above individually (fill "
        "per_learner_span): quote the learner's own words and mark it decisive, "
        "excessive, partial, or irrelevant with a reason. Then grade. Reply with "
        "ONLY the JSON object."
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
    learner_highlights: object = None,
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
    precision = _fallback_precision(
        passage, res["highlight"], gold_spans, selection_indices
    )
    highlights = _normalise_learner_highlights(learner_spans, learner_highlights)
    highlighted = [
        str(h.get("text", "")).strip()
        for h in highlights
        if str(h.get("text", "")).strip()
    ]
    intent = (
        "You appear to have focused on "
        + "; ".join(f'"{h}"' for h in highlighted[:3])
        if highlighted
        else "No evidence highlight was captured."
    )
    # Deterministic per-highlight critique so the shape matches the AI path even AI-off/on fallback.
    _, highlight_coverage = _coverage(passage, gold_spans, highlights)
    per_learner_span = _derive_per_learner_span(highlight_coverage)
    return {
        "ok": False,
        "source": "fallback",
        "grade": res["highlight"],
        "verdict_correct": res["verdict_correct"],
        "correct": res["correct"],
        "explanation": explanation,
        "coaching": coaching,
        "study_tip": study_tip,
        "learner_intent": intent,
        "evidence_precision": precision,
        "needed_evidence": phrases,
        "confidence": None,
        "per_span": per_span,
        "per_learner_span": per_learner_span,
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
    learner_highlights: object = None,
    max_tokens: int = 650,
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

    ``item_id`` is provenance the card supplies and ``standard`` is both prompt
    context and result provenance, so the UI can render the named governing
    Standard (e.g. "Graded by AI · II(A) Material Nonpublic Information"). The
    key is NEVER placed in the prompt or any returned value.

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
                learner_highlights=learner_highlights,
            )

    system = _SYSTEM_PROMPT
    user = _build_user_prompt(
        passage,
        answer_verdict,
        judged_verdict,
        gold_spans,
        learner_spans,
        selection_indices,
        learner_highlights,
        standard,
    )
    result = complete_fn(
        system=system,
        user=user,
        max_tokens=max_tokens,
        temperature=0.25,
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
            learner_highlights=learner_highlights,
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
            learner_highlights=learner_highlights,
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
    if grade in ("correct", "somewhat"):
        # By definition these grades mean every gold span was semantically
        # matched; don't let an omitted/malformed `spans` array make the UI show
        # "Correct" while marking each evidence span as missed.
        per_span = [
            {
                "phrase": row["phrase"],
                "matched": True,
                "note": row["note"] or gold_spans[i].get("rationale", ""),
            }
            for i, row in enumerate(per_span)
        ]

    explanation = str(parsed.get("explanation", "")).strip() or "Graded by AI."
    coaching = str(parsed.get("coaching", "")).strip()
    study_tip = str(parsed.get("study_tip", "")).strip()
    fallback_precision = _fallback_precision(
        passage, grade, gold_spans, selection_indices
    )
    learner_intent = str(parsed.get("learner_intent", "")).strip()
    evidence_precision = _clean_precision(
        parsed.get("evidence_precision"), fallback_precision
    )
    needed_raw = parsed.get("needed_evidence")
    if isinstance(needed_raw, list):
        needed_evidence = [str(x).strip() for x in needed_raw if str(x).strip()]
    else:
        needed_evidence = []
    if not needed_evidence:
        needed_evidence = phrases
    # Model may refine the named Standard; fall back to the card-supplied one.
    ai_standard = str(parsed.get("standard", "")).strip() or standard
    try:
        confidence = float(parsed.get("confidence"))
    except (TypeError, ValueError):
        confidence = None
    # Per-highlight critique — the payoff of the rework. Parse the model's per_learner_span (targeted
    # at what the learner actually highlighted) and pass it through ADDITIVELY, deriving a deterministic
    # row wherever the model omits or malforms one so the array is always keyed to the learner's spans.
    highlights = _normalise_learner_highlights(learner_spans, learner_highlights)
    _, highlight_coverage = _coverage(passage, gold_spans, highlights)
    per_learner_span = _parse_per_learner_span(
        parsed.get("per_learner_span"), _derive_per_learner_span(highlight_coverage)
    )
    return {
        "ok": True,
        "source": "ai",
        "grade": grade,
        "verdict_correct": ai_verdict_correct,
        "correct": correct,
        "explanation": explanation,
        "coaching": coaching,
        "study_tip": study_tip,
        "learner_intent": learner_intent,
        "evidence_precision": evidence_precision,
        "needed_evidence": needed_evidence,
        "confidence": confidence,
        "per_span": per_span,
        "per_learner_span": per_learner_span,
        "error": None,
        "model": result.get("model"),
        "item_id": item_id,
        "standard": ai_standard,
    }


__all__ = ["grade_semantic", "grade_fallback", "GRADES"]
