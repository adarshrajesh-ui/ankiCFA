#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A1 — does the AI grader actually beat a *simpler* baseline?

Runs the 30 human-labeled ethics-highlight attempts through three graders and
reports each one's agreement with the human 4-way highlight grade, side by side:

  1. **deterministic-span** — the shipped AI-off fallback
     (:func:`ai_grading.grade_fallback`): exact-phrase overlap of the learner's
     highlight against the gold evidence spans.
  2. **TF-IDF** — a genuinely *simpler* keyword baseline built here (stdlib
     only): cosine similarity in a TF-IDF space between each gold evidence span
     and the union of the learner's highlighted phrases. A gold span counts as
     covered when the cosine clears ``MATCH_THRESHOLD``; the covered fraction
     maps to a 4-way grade. This catches near-miss wording that exact matching
     drops, and can over-credit on shared common words (IDF down-weights those).
  3. **LLM (semantic)** — :func:`ai_grading.grade_semantic`, the real AI grader.

The point of the exercise: an LLM is only worth its cost if it *beats* a cheap
baseline. So when the LLM actually runs (``OPENAI_API_KEY`` set, or an injected
oracle in tests) the harness asserts

    llm_agreement > max(deterministic_agreement, tfidf_agreement)

and exits non-zero otherwise. With **AI OFF** there is no LLM to hold to that
bar, so the two baselines are reported honestly side by side and the LLM
assertion is SKIPPED — the documented AI-off contract, not a faked pass.

Usage:
    python cfa/eval/baseline_compare.py [--json] [--out FILE]
Exit code is non-zero only if the LLM ran and did NOT beat both baselines.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ETHICS = os.path.join(REPO, "cfa", "ethics_pairs")
sys.path.insert(0, ETHICS)
# make `cfa.ai.llm_client` importable from the repo root (grade_semantic uses it)
sys.path.insert(0, REPO)

import ai_grading as A  # noqa: E402
import eval_ai_grading as E  # noqa: E402

GRADES = A.GRADES  # ("correct", "somewhat", "partial", "wrong")

# A gold evidence span is "covered" once the learner's highlight clears this
# cosine similarity in the passage's TF-IDF space. Chosen so exact and close
# paraphrase matches count while incidental common-word overlap does not.
MATCH_THRESHOLD = 0.30

_WORD = re.compile(r"[a-z0-9']+")
# Common English words carry no evidence signal; drop them so cosine reflects the
# substantive terms (IDF also down-weights them, this just keeps vectors lean).
_STOP = frozenset(
    "a an and are as at be but by for from has have he her his in into is it its of "
    "on or she that the their them then there these they this to was were which who "
    "will with you your".split()
)


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall(str(text).lower()) if w not in _STOP]


def _sentences(passage: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", passage.strip()) if s.strip()]


def _idf(docs: list[list[str]]) -> dict[str, float]:
    n = len(docs) or 1
    df: Counter[str] = Counter()
    for d in docs:
        for w in set(d):
            df[w] += 1
    # smoothed idf; unseen terms fall back to the max idf at lookup time
    return {w: math.log((1 + n) / (1 + c)) + 1.0 for w, c in df.items()}


def _tfidf_vec(
    tokens: list[str], idf: dict[str, float], default_idf: float
) -> dict[str, float]:
    tf = Counter(tokens)
    return {w: c * idf.get(w, default_idf) for w, c in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def tfidf_grade(passage: str, gold_spans, learner_spans) -> dict:
    """A simpler keyword baseline: TF-IDF cosine coverage of the gold spans.

    Returns a dict shaped like the graders' results (``grade`` in GRADES plus a
    numeric ``coverage``), so the comparison harness can score it the same way.
    """
    phrases = [str(g.get("phrase", "")).strip() for g in gold_spans]
    phrases = [p for p in phrases if p]
    total = len(phrases)
    if total == 0:
        return {"grade": "wrong", "coverage": 0.0, "covered": 0, "total": 0}

    # IDF corpus = passage sentences + the gold phrases: enough documents for
    # term rarity to be meaningful within this one passage.
    corpus = [_tokens(s) for s in _sentences(passage)] + [_tokens(p) for p in phrases]
    idf = _idf(corpus)
    default_idf = max(idf.values(), default=1.0)

    learner_tokens = _tokens(" ".join(str(s) for s in learner_spans))
    learner_vec = _tfidf_vec(learner_tokens, idf, default_idf)

    covered = 0
    for p in phrases:
        gold_vec = _tfidf_vec(_tokens(p), idf, default_idf)
        if _cosine(gold_vec, learner_vec) >= MATCH_THRESHOLD:
            covered += 1

    frac = covered / total
    if frac >= 1.0:
        grade = "correct"
    elif frac >= 0.5:
        grade = "somewhat"
    elif frac > 0.0:
        grade = "partial"
    else:
        grade = "wrong"
    return {
        "grade": grade,
        "coverage": round(frac, 4),
        "covered": covered,
        "total": total,
    }


def run_compare(complete_fn=None) -> dict:
    """Grade every attempt with all three graders; return an agreement report."""
    passages = {r["item_id"]: r for r in E._load(E.PASSAGES)}
    attempts = E._load(E.ATTEMPTS)

    det_agree = tfidf_agree = llm_agree = 0
    ai_source = 0
    per_item = []

    for a in attempts:
        p = passages[a["item_id"]]
        human = a["human_grade"]

        det = A.grade_fallback(
            p["passage"],
            a["answer_verdict"],
            a["judged_verdict"],
            p["gold_spans"],
            a["learner_spans"],
        )
        tf = tfidf_grade(p["passage"], p["gold_spans"], a["learner_spans"])
        llm = A.grade_semantic(
            p["passage"],
            a["answer_verdict"],
            a["judged_verdict"],
            p["gold_spans"],
            a["learner_spans"],
            complete_fn=complete_fn,
        )

        if det["grade"] == human:
            det_agree += 1
        if tf["grade"] == human:
            tfidf_agree += 1
        if llm["grade"] == human:
            llm_agree += 1
        if llm["source"] == "ai":
            ai_source += 1

        per_item.append(
            {
                "item_id": a["item_id"],
                "human_grade": human,
                "deterministic": det["grade"],
                "tfidf": tf["grade"],
                "tfidf_coverage": tf["coverage"],
                "llm": llm["grade"],
                "llm_source": llm["source"],
            }
        )

    n = len(attempts)
    ran_ai = ai_source > 0
    return {
        "n": n,
        "ran_ai": ran_ai,
        "ai_source_count": ai_source,
        "match_threshold": MATCH_THRESHOLD,
        "deterministic_agreement": round(det_agree / n, 4) if n else 0.0,
        "tfidf_agreement": round(tfidf_agree / n, 4) if n else 0.0,
        "llm_agreement": round(llm_agree / n, 4) if n else 0.0,
        "per_item": per_item,
    }


def format_report(report: dict) -> str:
    det = report["deterministic_agreement"]
    tf = report["tfidf_agreement"]
    llm = report["llm_agreement"]
    best_baseline = max(det, tf)
    lines = []
    lines.append("=" * 70)
    lines.append("A1 — AI grader vs simpler baselines (ethics-highlight, 30 items)")
    lines.append("=" * 70)
    lines.append(f"attempts                 : {report['n']}")
    lines.append(f"tf-idf match threshold   : {report['match_threshold']:.2f} cosine")
    lines.append("")
    lines.append("grade agreement with the human 4-way label (higher is better):")
    lines.append(f"  deterministic-span     : {det:.3f}   (exact-phrase, AI-off)")
    lines.append(f"  TF-IDF keyword         : {tf:.3f}   (simpler baseline)")
    if report["ran_ai"]:
        lines.append(f"  LLM (semantic)         : {llm:.3f}   (AI grader)")
    else:
        lines.append("  LLM (semantic)         :  ---    (AI OFF — no OPENAI_API_KEY)")
    lines.append("")
    if report["ran_ai"]:
        ok = llm > best_baseline
        verdict = "PASS: AI beats the baseline" if ok else "FAIL: AI loses to baseline"
        lines.append(
            f"LLM {llm:.3f} {'>' if ok else '<='} best baseline "
            f"{best_baseline:.3f} -> {verdict}"
        )
    else:
        lines.append(
            "AI OFF: no OPENAI_API_KEY, so the 'AI beats the baseline' assertion is "
            "SKIPPED. The two baselines above are the honest AI-off numbers; the "
            "deterministic-span grader is what actually ships when AI is off."
        )
    lines.append("=" * 70)
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="A1 AI-vs-baseline comparison")
    ap.add_argument("--json", action="store_true", help="emit the raw report as JSON")
    ap.add_argument("--out", help="also write the text report to this file")
    args = ap.parse_args(argv)

    report = run_compare()
    text = format_report(report)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")

    # Only fail when the LLM actually ran and failed to beat both baselines.
    if report["ran_ai"]:
        best = max(report["deterministic_agreement"], report["tfidf_agreement"])
        if report["llm_agreement"] <= best:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
