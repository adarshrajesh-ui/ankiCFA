# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Author the F2 human-labeled gold-set of 30 ethics-highlight attempts.

Each row is one realistic learner attempt at a passage: the verdict they chose
and the passage substrings they highlighted, plus a HUMAN grade label (the grade
a CFA ethics expert says that highlight deserves) and the overall human_correct
call. The attempts deliberately span the grade tiers AND include several
"semantic-win" cases: attempts a human grades ``correct`` because the learner
clearly identified the right evidence, but whose token boundaries differ from the
gold phrase so the deterministic F1 grader under-scores them. Those are exactly
what the F2 semantic grader is meant to rescue.

Run this to regenerate eval_attempts.jsonl; it fails loudly if any highlighted
phrase is not a verbatim substring of its passage (a learner can only highlight
real passage words), so the gold-set stays honest.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ethics_scoring import (  # noqa: E402
    PassageAttempt,
    find_gold_spans,
    grade_passage_attempt,
)

PASSAGES = os.path.join(HERE, "passages.jsonl")
OUT = os.path.join(HERE, "eval_attempts.jsonl")

# (item_id, judged_verdict, [learner highlighted phrases], human_grade, note)
# human_correct is derived: verdict right AND human_grade == "correct".
ATTEMPTS = [
    # --- SEMANTIC WIN: right evidence, boundaries differ -> deterministic under-scores
    (
        "PSG-01",
        "unethical",
        ["unreleased quarterly earnings figure", "sells the company"],
        "correct",
        "Identified the MNPI (the earnings figure) and the trade; boundaries clipped.",
    ),
    (
        "PSG-02",
        "ethical",
        [
            "expressly authorizes high-risk illiquid alternatives",
            "long horizon and ample liquidity elsewhere",
            "confirming the position fits the stated mandate",
        ],
        "correct",
        "Exact evidence for a suitable, mandate-authorized placement.",
    ),
    (
        "PSG-03",
        "unethical",
        [
            "confidential, still-secret projection",
            "market-moving earnings surge",
            "tells him to buy Vantex shares",
        ],
        "correct",
        "Nailed the MNPI and the tip-and-trade.",
    ),
    (
        "PSG-04",
        "ethical",
        [
            "information barrier",
            "never mentions any deal",
            "her own published valuation work",
        ],
        "correct",
        "SEMANTIC WIN: 'information barrier' clips the gold phrase but is the right evidence.",
    ),
    (
        "PSG-05",
        "unethical",
        [
            "a single report",
            "without checking any of it",
            "issues a strong buy on Halcyon",
        ],
        "correct",
        "SEMANTIC WIN: clipped boundaries on two spans, but the diligence failure is identified.",
    ),
    (
        "PSG-06",
        "ethical",
        ["studying the pricing model's volatility and correlation assumptions"],
        "partial",
        "Only one of three diligence steps highlighted.",
    ),
    (
        "PSG-07",
        "unethical",
        [
            "recently lost his job and now needs near-term liquidity",
            "applies the firm's standard growth-tilted model portfolio",
            "without revisiting his written IPS",
        ],
        "correct",
        "All three suitability-failure spans exact.",
    ),
    (
        "PSG-08",
        "ethical",
        [
            "first discusses the suitability mismatch with her",
            "documents that conversation before executing the unsolicited order",
        ],
        "correct",
        "Both compliance actions exact.",
    ),
    (
        "PSG-09",
        "unethical",
        [
            "signed a definitive agreement",
            "information not yet announced",
            "buys Crestline shares",
        ],
        "correct",
        "SEMANTIC WIN: trade span clipped ('for her clients' omitted) but clearly the act.",
    ),
    (
        "PSG-10",
        "ethical",
        [
            "written mandate authorizes a currency-hedging derivative overlay",
            "against the mandate and constraints in a total-portfolio context",
            "confirms it lowers overall risk",
        ],
        "correct",
        "Exact evidence of authorized, risk-reducing derivative use.",
    ),
    (
        "PSG-11",
        "unethical",
        ["without any citation", "original macroeconomic forecast"],
        "correct",
        "SEMANTIC WIN: second span clips 'and interpretation' but names the copied original work.",
    ),
    (
        "PSG-12",
        "ethical",
        ["fixed and contractually assured", "under its written terms"],
        "correct",
        "Both spans exact: the guarantee is factually true.",
    ),
    (
        "PSG-13",
        "unethical",
        [
            "Reuben commissions an independent writer to produce a detailed sector report",
            "strips the writer's byline",
            "and distributes it to his clients under his own name as his personal work",
        ],
        "somewhat",
        "Both gold spans covered but the whole passage is dragged in.",
    ),
    (
        "PSG-14",
        "ethical",
        ["with a clear label", "earned while she was employed at her prior firm"],
        "correct",
        "Both disclosure spans exact.",
    ),
    (
        "PSG-15",
        "unethical",
        [
            "quietly excludes several terminated and money-losing accounts",
            "boosting the reported figure above what all qualifying accounts actually earned",
        ],
        "correct",
        "Both misrepresentation spans exact.",
    ),
    (
        "PSG-16",
        "ethical",
        ["as the fund's manager", "full managerial responsibility for it"],
        "correct",
        "Both truthful-credential spans exact.",
    ),
    (
        "PSG-17",
        "unethical",
        ["In a client presentation, Oksana"],
        "wrong",
        "Highlighted the setup, not the plagiarism evidence.",
    ),
    (
        "PSG-18",
        "ethical",
        ["set off in quotation marks", "clearly attributed to that strategist by name"],
        "correct",
        "Both attribution spans exact.",
    ),
    (
        "PSG-19",
        "unethical",
        [
            "the note's principal is fully guaranteed",
            "no such principal guarantee",
            "its value can fall",
        ],
        "correct",
        "SEMANTIC WIN: third span clips 'with the underlying index' but states the risk.",
    ),
    (
        "PSG-20",
        "ethical",
        [
            "clearly disclosing that the recommendation originated",
            "third-party research provider",
        ],
        "correct",
        "SEMANTIC WIN: both spans clipped, but the disclosure of the outside source is identified.",
    ),
    (
        "PSG-21",
        "unethical",
        [
            "for his own account in the morning",
            "improving the fill on his earlier personal purchase",
        ],
        "correct",
        "Both front-running spans exact.",
    ),
    (
        "PSG-22",
        "ethical",
        [
            "pro rata to all eligible client accounts",
            "pre-established written allocation policy",
            "excludes his own and his family's beneficial accounts",
        ],
        "correct",
        "All three fair-allocation spans exact.",
    ),
    (
        "PSG-23",
        "ethical",  # WRONG VERDICT: spans right, verdict wrong
        [
            "Monday morning she buys call options",
            "then submits the client block order Monday afternoon",
        ],
        "correct",
        "Highlight is right but the verdict is wrong -> not overall correct.",
    ),
    (
        "PSG-24",
        "ethical",
        [
            "allocates fills to all client accounts first",
            "treats his brother's account exactly like the clients",
            "with no preferential timing or pricing",
        ],
        "correct",
        "All three fair-treatment spans exact.",
    ),
    (
        "PSG-25",
        "unethical",
        ["takes a personal allocation for her own account"],
        "correct",
        "SEMANTIC WIN: one span clips 'before' but plainly captures the self-preference.",
    ),
    (
        "PSG-26",
        "ethical",
        [
            "a written notice disclosing",
            "client buy orders in the stock first",
            "only afterward buys additional shares for his own account",
        ],
        "correct",
        "All three priority-of-transactions spans exact.",
    ),
    (
        "PSG-27",
        "unethical",
        ["fills her own personal Ironpeak order first"],
        "partial",
        "Got the personal-first span but missed the client-after span.",
    ),
    (
        "PSG-28",
        "ethical",
        ["pro rata across the client accounts", "takes any personal allocation last"],
        "correct",
        "Both fair-priority spans exact.",
    ),
    (
        "PSG-29",
        "unethical",
        [
            "in which he holds a beneficial interest",
            "letting it fill ahead of the client order",
        ],
        "correct",
        "Both front-running spans exact.",
    ),
    (
        "PSG-30",
        "ethical",
        [
            "promptly executes the client's order",
            "only afterward submits her own personal buy",
        ],
        "correct",
        "Both client-priority spans exact.",
    ),
]


def main() -> int:
    passages = {}
    with open(PASSAGES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                passages[r["item_id"]] = r

    rows = []
    det_agree = 0
    seen = set()
    for item_id, judged, learner_spans, human_grade, note in ATTEMPTS:
        assert item_id not in seen, f"duplicate {item_id}"
        seen.add(item_id)
        p = passages[item_id]
        passage = p["passage"]
        # every highlighted phrase MUST be verbatim in the passage
        for phrase in learner_spans:
            assert phrase in passage, (
                f"{item_id}: '{phrase}' not a substring of the passage"
            )
        human_correct = (judged == p["verdict"]) and human_grade == "correct"

        # cross-check what the deterministic grader would say (for the report only)
        gold_phrases = [g["phrase"] for g in p["gold_spans"]]
        gold_runs = find_gold_spans(passage, gold_phrases)
        sel = [i for run in find_gold_spans(passage, learner_spans) for i in run]
        det = grade_passage_attempt(
            PassageAttempt(judged, p["verdict"], sel, gold_runs)
        )
        det_grade = det["highlight"]
        if det_grade == human_grade:
            det_agree += 1

        rows.append(
            {
                "item_id": item_id,
                "judged_verdict": judged,
                "answer_verdict": p["verdict"],
                "learner_spans": learner_spans,
                "human_grade": human_grade,
                "human_correct": human_correct,
                "deterministic_grade_preview": det_grade,
                "note": note,
            }
        )

    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} labeled attempts -> {OUT}")
    print(
        f"deterministic-vs-human grade agreement (preview): {det_agree}/{len(rows)} "
        f"= {det_agree / len(rows):.3f}"
    )
    semantic_wins = sum(
        1 for r in rows if r["deterministic_grade_preview"] != r["human_grade"]
    )
    print(f"semantic-win cases (deterministic under-scores vs human): {semantic_wins}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
