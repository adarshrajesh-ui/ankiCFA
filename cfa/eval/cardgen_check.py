#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A6 — card-generation gold-set checker (block bad AI-drafted cards).

The AI "tab-to-fill" feature (:mod:`qt.aqt.cfa_tab_fill`) drafts a card *back*
from a *front*. A generator that quietly emits wrong or useless cards is worse
than no generator at all, so before any batch of AI-drafted cards is trusted we
run it through a **gold-set checker with a cutoff declared up front** and
**block the batch** if it does not clear the bar.

Pipeline
--------
1. ``cfa/eval/cardgen_gold.jsonl`` — 50 known-correct CFA Q&A drawn from the
   already-vetted study deck (``cfa/deck/*.jsonl``). Each row is a *source*:
   a ``front`` (question) and the canonical ``gold_back`` (correct answer).
2. A generator drafts a back for each front. Two generators exist:
     * **real** — :func:`qt.aqt.cfa_tab_fill.draft_back` via an injected /
       default ``complete_fn`` (AI ON, or an oracle in tests).
     * **SIMULATED** — a seeded, deterministic generator used when AI is OFF so
       the checker + gate are still exercised end-to-end. Clearly labelled
       ``SIMULATED``; it never pretends to be a real model.
3. :func:`classify_card` independently buckets each *(gold, generated)* pair
   into one of three buckets — this is the honest measurement, taken by the
   checker, not by the generator:
     * ``correct_useful``   — captures the gold answer's core facts AND is a
       well-formed flashcard back.
     * ``correct_but_bad``  — captures the facts but is a poor card (a stub,
       a rambling wall of text, or it just parrots the question).
     * ``wrong``            — misses the core facts / off-topic / empty.

Cutoff (declared up front, see :data:`USEFUL_CUT` / :data:`WRONG_CUT`)::

    PASS  iff  correct_useful_fraction >= 0.80  AND  wrong_fraction <= 0.10

If the batch fails either bar the gate **blocks** it (non-zero exit) when a real
generator ran. With AI OFF the SIMULATED run reports the same numbers honestly
and exits 0 (it is a measurement of the checker/simulator, not a real batch of
cards being admitted). The give-up rule: with fewer than
:data:`MIN_GOLD` gold rows the checker abstains rather than guessing.

Usage::

    python cfa/eval/cardgen_check.py [--json] [--out FILE] [--seed N]
                                     [--generate] [--bad-sim]

Exit code is non-zero only when a real generator ran and the batch failed the
cutoff (i.e. bad cards were blocked).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
GOLD_PATH = os.path.join(HERE, "cardgen_gold.jsonl")

# --- declared cutoff (up front, not tuned after the fact) --------------------
USEFUL_CUT = 0.80  # >= 80% of drafted cards must be correct AND useful
WRONG_CUT = 0.10  # <= 10% of drafted cards may be factually wrong
MIN_GOLD = 20  # give-up rule: abstain below this many gold rows

BUCKETS = ("correct_useful", "correct_but_bad", "wrong")

# --- classifier thresholds ---------------------------------------------------
# A drafted back must recover at least this fraction of the gold answer's
# salient content terms, else it is judged to have missed the core facts.
COVERAGE_WRONG = 0.40
# Quality bounds for a card back that IS factually on-target.
MIN_USEFUL_CHARS = 15
MIN_USEFUL_WORDS = 3
# A back this many times longer than the gold answer (and past an absolute
# floor) is a rambling wall of text — correct, maybe, but a bad flashcard.
LONG_RATIO = 4.0
LONG_ABS_CHARS = 600
# If the draft is mostly the question echoed back (high overlap with the front,
# little new content) it is circular — a bad card even if "not wrong".
ECHO_FRONT_OVERLAP = 0.80

_WORD = re.compile(r"[a-z0-9']+")
_STOP = frozenset(
    "a an and are as at be but by for from has have he her his in into is it its of "
    "on or she that the their them then there these they this to was were what which "
    "who will with you your no not do does".split()
)


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall(str(text).lower()) if w not in _STOP]


def load_gold(path: str = GOLD_PATH) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# --- the checker -------------------------------------------------------------


def coverage(gold_back: str, generated: str) -> float:
    """Fraction of the gold answer's salient terms present in the draft."""
    gold_terms = set(_tokens(gold_back))
    if not gold_terms:
        return 0.0
    gen_terms = set(_tokens(generated))
    return len(gold_terms & gen_terms) / len(gold_terms)


def _front_echo_overlap(front: str, generated: str) -> float:
    """Fraction of the *draft's* terms that merely repeat the question."""
    gen_terms = set(_tokens(generated))
    if not gen_terms:
        return 0.0
    front_terms = set(_tokens(front))
    return len(gen_terms & front_terms) / len(gen_terms)


def classify_card(gold_back: str, generated: str, front: str = "") -> dict:
    """Bucket one drafted back against its gold answer.

    Returns ``{"bucket", "coverage", "reason"}`` where ``bucket`` is one of
    :data:`BUCKETS`. Correctness (coverage of the gold facts) is checked first;
    only an on-target draft can then fail on card *quality*.
    """
    gen = (generated or "").strip()
    cov = coverage(gold_back, gen)

    # --- wrong: empty or misses the core facts ---
    if not gen:
        return {"bucket": "wrong", "coverage": 0.0, "reason": "empty"}
    if cov < COVERAGE_WRONG:
        return {
            "bucket": "wrong",
            "coverage": round(cov, 4),
            "reason": f"coverage {cov:.2f} < {COVERAGE_WRONG:.2f}",
        }

    # --- correct-but-bad: on-target facts, poor as a flashcard ---
    words = _tokens(gen)
    if len(gen) < MIN_USEFUL_CHARS or len(words) < MIN_USEFUL_WORDS:
        return {"bucket": "correct_but_bad", "coverage": round(cov, 4),
                "reason": "too short / stub"}
    if len(gen) > LONG_ABS_CHARS and len(gen) > LONG_RATIO * max(1, len(gold_back)):
        return {"bucket": "correct_but_bad", "coverage": round(cov, 4),
                "reason": "rambling / too long"}
    if front and _front_echo_overlap(front, gen) >= ECHO_FRONT_OVERLAP:
        return {"bucket": "correct_but_bad", "coverage": round(cov, 4),
                "reason": "circular / echoes the question"}

    return {"bucket": "correct_useful", "coverage": round(cov, 4), "reason": "ok"}


# --- generators --------------------------------------------------------------


def _hash01(*parts: object) -> float:
    """Deterministic float in [0,1) from the parts (no PRNG state)."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16) / 0x100000000


def simulate_generation(
    gold: list[dict], seed: int = 0, bad: bool = False
) -> list[str]:
    """Deterministically fabricate a batch of card backs from the gold set.

    Produces a realistic mix so the checker + gate are exercised without any
    network. Every string returned is a *simulated* generator output; the
    checker classifies them independently. ``bad=True`` skews the mix so the
    gate fails, demonstrating that bad batches are blocked.

    The mix is assigned by *rank* of a stable per-row hash so the counts are
    exact and reproducible (not merely expected):
      * a fixed few -> another item's answer      (checker -> wrong)
      * a fixed few -> a stub or a rambling dump   (checker -> correct_but_bad)
      * the rest    -> the correct answer          (checker -> correct_useful)
    """
    n = len(gold)
    wrong_n = round((0.40 if bad else 0.08) * n)
    bad_n = round((0.10 if bad else 0.08) * n)
    # rank rows by hash to pick which get the wrong / poor-quality treatment
    order = sorted(range(n), key=lambda i: _hash01(seed, gold[i]["id"]))
    wrong_idx = set(order[:wrong_n])
    bad_idx = set(order[wrong_n:wrong_n + bad_n])
    out = []
    for i, g in enumerate(gold):
        if i in wrong_idx:
            # a plausible-but-wrong draft: a *different* item's gold answer
            decoy = gold[(i + 1 + wrong_n) % n]
            out.append(decoy["gold_back"])
        elif i in bad_idx:
            # a poor card that still CONTAINS the gold facts (coverage high) but
            # is a bad flashcard: a rambling wall of text. The checker buckets it
            # correct_but_bad, not wrong. (The too-short/stub quality path is
            # covered directly in the unit tests, where coverage stays high.)
            out.append((g["gold_back"] + " ") * 8)
        else:
            out.append(g["gold_back"])
    return out


def _load_draft_back():
    """Load ``qt/aqt/cfa_tab_fill.draft_back`` WITHOUT importing the ``aqt``
    package (whose ``__init__`` pulls in ``anki``, unavailable offline).

    We execute the single module file directly by path — it is the exact same
    generator the desktop editor ships, but it imports cleanly under a bare
    pytest because its only runtime dependency (``cfa.ai.tabfill``) is stdlib.
    """
    import importlib.util

    path = os.path.join(REPO, "qt", "aqt", "cfa_tab_fill.py")
    sys.path.insert(0, REPO)  # so its `from cfa.ai.tabfill import ...` resolves
    spec = importlib.util.spec_from_file_location("cfa_tab_fill_a6", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.draft_back


def generate_real(gold: list[dict], complete_fn=None) -> tuple[list[str], bool]:
    """Draft each back with the real (or injected-oracle) generator.

    Returns ``(backs, ran_ai)``. ``ran_ai`` is True iff at least one draft came
    back from the model; a failed/AI-off draft yields an empty string (which the
    checker buckets as ``wrong``)."""
    draft_back = _load_draft_back()

    backs, ran_ai = [], False
    for g in gold:
        res = draft_back(g["front"], complete_fn=complete_fn)
        if res.get("ok"):
            ran_ai = True
            backs.append(res.get("text", ""))
        else:
            backs.append("")
    return backs, ran_ai


# --- run + report ------------------------------------------------------------


def run_check(gold: list[dict], generated: list[str], ran_ai: bool,
              simulated: bool) -> dict:
    counts = {b: 0 for b in BUCKETS}
    per_item = []
    for g, gen in zip(gold, generated):
        res = classify_card(g["gold_back"], gen, g.get("front", ""))
        counts[res["bucket"]] += 1
        per_item.append({
            "id": g["id"], "topic": g.get("topic", ""),
            "bucket": res["bucket"], "coverage": res["coverage"],
            "reason": res["reason"],
        })
    n = len(gold)
    abstain = n < MIN_GOLD
    useful_frac = counts["correct_useful"] / n if n else 0.0
    wrong_frac = counts["wrong"] / n if n else 0.0
    gate_pass = (useful_frac >= USEFUL_CUT) and (wrong_frac <= WRONG_CUT)
    return {
        "n": n,
        "abstain": abstain,
        "simulated": simulated,
        "ran_ai": ran_ai,
        "counts": counts,
        "correct_useful_fraction": round(useful_frac, 4),
        "correct_but_bad_fraction": (
            round(counts["correct_but_bad"] / n, 4) if n else 0.0
        ),
        "wrong_fraction": round(wrong_frac, 4),
        "useful_cut": USEFUL_CUT,
        "wrong_cut": WRONG_CUT,
        "gate_pass": gate_pass,
        "per_item": per_item,
    }


def format_report(report: dict) -> str:
    c = report["counts"]
    lines = []
    lines.append("=" * 70)
    lines.append("A6 — card-generation gold-set checker (50 known-correct CFA QA)")
    lines.append("=" * 70)
    tag = "SIMULATED generator (AI OFF)" if report["simulated"] else (
        "REAL generator (AI ON)" if report["ran_ai"] else "generator produced no cards")
    lines.append(f"generator                : {tag}")
    lines.append(f"gold cards               : {report['n']}")
    if report["abstain"]:
        lines.append("")
        lines.append(f"ABSTAIN: fewer than {MIN_GOLD} gold rows — insufficient data "
                     "to judge the generator (give-up rule).")
        lines.append("=" * 70)
        return "\n".join(lines)
    lines.append(f"declared cutoff          : correct_useful >= {USEFUL_CUT:.0%} "
                 f"AND wrong <= {WRONG_CUT:.0%}")
    lines.append("")
    lines.append("checker buckets (independent of the generator):")
    lines.append(f"  correct + useful       : {c['correct_useful']:>3}  "
                 f"({report['correct_useful_fraction']:.1%})")
    lines.append(f"  correct but bad card   : {c['correct_but_bad']:>3}  "
                 f"({report['correct_but_bad_fraction']:.1%})")
    lines.append(f"  wrong                  : {c['wrong']:>3}  "
                 f"({report['wrong_fraction']:.1%})")
    lines.append("")
    verdict = "PASS" if report["gate_pass"] else "FAIL — batch BLOCKED"
    lines.append(f"gate: useful {report['correct_useful_fraction']:.1%} "
                 f">= {USEFUL_CUT:.0%}? "
                 f"{report['correct_useful_fraction'] >= USEFUL_CUT}  |  "
                 f"wrong {report['wrong_fraction']:.1%} <= {WRONG_CUT:.0%}? "
                 f"{report['wrong_fraction'] <= WRONG_CUT}  ->  {verdict}")
    if report["simulated"]:
        lines.append("")
        lines.append("Note: SIMULATED — no LLM ran; the generator output is fabricated "
                     "(labelled SIMULATED) purely to exercise the checker and gate. "
                     "The bucket counts above are the checker's honest judgement of "
                     "that fabricated batch. With a real generator (AI ON) a failing "
                     "batch is blocked (non-zero exit).")
    lines.append("=" * 70)
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="A6 card-generation gold-set checker")
    ap.add_argument("--json", action="store_true", help="emit the raw report as JSON")
    ap.add_argument("--out", help="also write the text report to this file")
    ap.add_argument("--seed", type=int, default=0, help="SIMULATED generator seed")
    ap.add_argument("--generate", action="store_true",
                    help="use the REAL generator (draft_back); AI-off -> empty backs")
    ap.add_argument("--bad-sim", action="store_true",
                    help="SIMULATED: skew the mix so the gate fails (demo blocking)")
    args = ap.parse_args(argv)

    gold = load_gold()
    if args.generate:
        generated, ran_ai = generate_real(gold)
        simulated = False
    else:
        generated = simulate_generation(gold, seed=args.seed, bad=args.bad_sim)
        ran_ai = False
        simulated = True

    report = run_check(gold, generated, ran_ai=ran_ai, simulated=simulated)
    text = format_report(report)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")

    if report["abstain"]:
        return 0
    # Block only a REAL batch that failed the cutoff. A SIMULATED run is a
    # measurement of the checker itself, so it always exits 0 (honest AI-off).
    if report["ran_ai"] and not report["gate_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
