# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F2 eval — measure how well the ethics-highlight grader agrees with humans.

Runs every attempt in ``eval_attempts.jsonl`` (30 human-labeled highlights)
through :func:`ai_grading.grade_semantic` and compares the grader's 4-way
highlight grade against the human label, printing:

  * grade agreement (primary metric),
  * overall correct/incorrect accuracy,
  * a per-tier confusion breakdown,
  * the deterministic baseline (from the frozen preview column) for contrast.

When ``OPENAI_API_KEY`` is set the LLM grades and the harness asserts LLM
agreement >= 0.8 (the F2 acceptance bar). With AI OFF the deterministic fallback
grades instead; the harness reports its agreement honestly and SKIPS the LLM
assertion (there is no LLM to hold to the bar) — this is the documented AI-off
contract, not a pass being faked.

Usage:
    python cfa/ethics_pairs/eval_ai_grading.py [--json] [--threshold 0.8]
Exit code is non-zero only if the LLM ran and missed the threshold.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# make `cfa.ai.llm_client` importable from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from ai_grading import grade_semantic  # noqa: E402

ATTEMPTS = os.path.join(HERE, "eval_attempts.jsonl")
PASSAGES = os.path.join(HERE, "passages.jsonl")
GRADES = ("correct", "somewhat", "partial", "wrong")

# --- A2 named acceptance gate (cutoffs declared up front) --------------------
# ACCURACY_CUT: the grader must agree with the human correct/incorrect verdict
#   on at least this fraction of attempts.
# WRONG_ANSWER_RATE_CUT: of the attempts a human marked INCORRECT, at most this
#   fraction may be "false-accepted" (grader says correct). This is the most
#   dangerous grading error for an exam-prep product — telling a student a wrong
#   answer is right — so it gets its own hard ceiling on top of raw accuracy.
ACCURACY_CUT = 0.80
WRONG_ANSWER_RATE_CUT = 0.20


def _ai_available() -> bool:
    if os.environ.get("OPENAI_API_KEY"):
        return True
    # mirror llm_client's .env fallback without importing its private loader
    env_path = os.path.join(os.path.dirname(os.path.dirname(HERE)), ".env")
    if os.path.isfile(env_path):
        try:
            for line in open(env_path, encoding="utf-8"):
                if line.strip().startswith("OPENAI_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return True
        except OSError:
            return False
    return False


def _load(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def run_eval(complete_fn=None) -> dict:
    """Grade every labeled attempt and return a report dict. Never raises."""
    passages = {r["item_id"]: r for r in _load(PASSAGES)}
    attempts = _load(ATTEMPTS)

    per_item = []
    grade_agree = 0
    correct_agree = 0
    det_agree = 0
    ai_source = 0
    human_incorrect = 0
    false_accepts = 0
    confusion: dict[str, dict[str, int]] = {h: {g: 0 for g in GRADES} for h in GRADES}

    for a in attempts:
        p = passages[a["item_id"]]
        res = grade_semantic(
            p["passage"],
            a["answer_verdict"],
            a["judged_verdict"],
            p["gold_spans"],
            a["learner_spans"],
            complete_fn=complete_fn,
        )
        g = res["grade"]
        h = a["human_grade"]
        if g == h:
            grade_agree += 1
        if bool(res["correct"]) == bool(a["human_correct"]):
            correct_agree += 1
        if not bool(a["human_correct"]):
            human_incorrect += 1
            if bool(res["correct"]):
                false_accepts += 1
        if a.get("deterministic_grade_preview") == h:
            det_agree += 1
        if res["source"] == "ai":
            ai_source += 1
        if h in confusion and g in confusion[h]:
            confusion[h][g] += 1
        per_item.append(
            {
                "item_id": a["item_id"],
                "human_grade": h,
                "grader_grade": g,
                "source": res["source"],
                "human_correct": a["human_correct"],
                "grader_correct": res["correct"],
                "explanation": res["explanation"],
            }
        )

    n = len(attempts)
    ran_ai = ai_source > 0
    # wrong_answer_rate: false-accepts of human-incorrect answers. Undefined
    # (0.0, reported honestly with the denominator) when no human-incorrect
    # attempts exist in the gold set.
    war = round(false_accepts / human_incorrect, 4) if human_incorrect else 0.0
    accuracy = round(correct_agree / n, 4) if n else 0.0
    gate_pass = accuracy >= ACCURACY_CUT and war <= WRONG_ANSWER_RATE_CUT
    return {
        "n": n,
        "ran_ai": ran_ai,
        "ai_source_count": ai_source,
        "grade_agreement": round(grade_agree / n, 4) if n else 0.0,
        "correct_accuracy": accuracy,
        "deterministic_baseline_agreement": round(det_agree / n, 4) if n else 0.0,
        "human_incorrect": human_incorrect,
        "false_accepts": false_accepts,
        "wrong_answer_rate": war,
        "accuracy_cut": ACCURACY_CUT,
        "wrong_answer_rate_cut": WRONG_ANSWER_RATE_CUT,
        "gate_pass": gate_pass,
        "confusion": confusion,
        "per_item": per_item,
    }


def format_report(report: dict, threshold: float) -> str:
    lines = []
    lines.append("=" * 68)
    lines.append("F2 ethics-highlight grading eval — human-labeled gold-set")
    lines.append("=" * 68)
    grader = "LLM (semantic)" if report["ran_ai"] else "deterministic fallback (AI OFF)"
    lines.append(f"attempts            : {report['n']}")
    lines.append(f"active grader       : {grader}")
    lines.append(f"grade agreement     : {report['grade_agreement']:.3f}")
    lines.append(f"overall accuracy    : {report['correct_accuracy']:.3f}")
    lines.append(
        f"deterministic base  : {report['deterministic_baseline_agreement']:.3f} "
        "(frozen preview, for contrast)"
    )
    lines.append(
        f"wrong-answer rate   : {report['wrong_answer_rate']:.3f} "
        f"({report['false_accepts']}/{report['human_incorrect']} human-incorrect "
        "answers false-accepted)"
    )
    lines.append("")
    lines.append("confusion (rows=human, cols=grader):")
    header = "            " + "".join(f"{g:>10}" for g in GRADES)
    lines.append(header)
    for h in GRADES:
        row = f"  {h:>9} " + "".join(f"{report['confusion'][h][g]:>10}" for g in GRADES)
        lines.append(row)
    lines.append("")
    # A2 named acceptance gate: accuracy >= ACCURACY_CUT AND
    # wrong_answer_rate <= WRONG_ANSWER_RATE_CUT.
    acc_ok = report["correct_accuracy"] >= report["accuracy_cut"]
    war_ok = report["wrong_answer_rate"] <= report["wrong_answer_rate_cut"]
    lines.append("A2 named gate (cutoffs declared up front):")
    lines.append(
        f"  accuracy          {report['correct_accuracy']:.3f} "
        f"{'>=' if acc_ok else '<'} {report['accuracy_cut']:.2f} "
        f"-> {'PASS' if acc_ok else 'FAIL'}"
    )
    lines.append(
        f"  wrong-answer rate {report['wrong_answer_rate']:.3f} "
        f"{'<=' if war_ok else '>'} {report['wrong_answer_rate_cut']:.2f} "
        f"-> {'PASS' if war_ok else 'FAIL'}"
    )
    lines.append(
        f"  gate ({'AI' if report['ran_ai'] else 'AI-OFF deterministic'}) -> "
        f"{'PASS' if report['gate_pass'] else 'FAIL'}"
    )
    lines.append("")
    if report["ran_ai"]:
        ok = report["grade_agreement"] >= threshold
        lines.append(
            f"LLM agreement {report['grade_agreement']:.3f} "
            f"{'>=' if ok else '<'} threshold {threshold:.2f} -> "
            f"{'PASS' if ok else 'FAIL'}"
        )
    else:
        lines.append(
            f"AI OFF: no OPENAI_API_KEY, so the LLM >= {threshold:.2f} assertion is "
            "SKIPPED. The deterministic fallback graded every attempt; its agreement "
            "is reported above and is the honest AI-off number."
        )
    lines.append("=" * 68)
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F2 ethics-highlight grading eval")
    ap.add_argument("--json", action="store_true", help="emit the raw report as JSON")
    ap.add_argument("--threshold", type=float, default=0.8)
    args = ap.parse_args(argv)

    report = run_eval()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_report(report, args.threshold))

    # Only fail the process when the LLM actually ran and missed a bar — either
    # the grade-agreement threshold or the A2 named gate (accuracy +
    # wrong-answer rate). AI-off reports the deterministic numbers honestly and
    # never fails the process (the documented AI-off contract).
    if report["ran_ai"] and (
        report["grade_agreement"] < args.threshold or not report["gate_pass"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
