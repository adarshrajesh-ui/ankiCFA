#!/usr/bin/env python3
"""Leakage check for the held-out CFA eval set.

A held-out evaluation is only meaningful if its questions were never part of
the training deck. This script verifies two things and exits non-zero on any
violation:

  1. Every held-out ``los_tag`` is actually covered by the training deck
     (so we are evaluating concepts the learner studied), AND
  2. No held-out question is a near-duplicate of any training-deck ``front``
     (so the exact wording was never seen). "Near-duplicate" is measured by
     Jaccard overlap of lowercased alphanumeric tokens; anything at or above
     ``LEAK_THRESHOLD`` is flagged as leakage.

Stdlib only — no build required.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HELDOUT = os.path.join(HERE, "heldout.jsonl")
DECK_GLOB = os.path.join(REPO, "cfa", "deck", "items-*.jsonl")

# Jaccard overlap at/above this fraction between a held-out question and a deck
# front counts as leakage (the test wording was effectively in training).
LEAK_THRESHOLD = 0.6

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _load_jsonl(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def check(heldout_path: str = HELDOUT, verbose: bool = True) -> list[str]:
    """Return a list of violation strings (empty == clean)."""
    heldout = _load_jsonl(heldout_path)

    deck_fronts: list[tuple[str, set[str]]] = []
    deck_tags: set[str] = set()
    for path in sorted(glob.glob(DECK_GLOB)):
        for item in _load_jsonl(path):
            front = item.get("front", "")
            deck_fronts.append((front, _tokens(front)))
            deck_tags.add(item.get("los_tag", ""))

    violations: list[str] = []

    for item in heldout:
        cid = item.get("concept_id", "?")
        tag = item.get("los_tag", "")
        if tag not in deck_tags:
            violations.append(
                f"{cid}: los_tag {tag!r} is not covered by the training deck"
            )
        for variant in ("question_a", "question_b"):
            q = item.get(variant, "")
            qt = _tokens(q)
            worst = 0.0
            worst_front = ""
            for front, ft in deck_fronts:
                j = _jaccard(qt, ft)
                if j > worst:
                    worst, worst_front = j, front
            if worst >= LEAK_THRESHOLD:
                violations.append(
                    f"{cid}/{variant}: {worst:.2f} token overlap with deck "
                    f"front {worst_front!r}"
                )

    if verbose:
        n_q = 2 * len(heldout)
        print(f"held-out concepts: {len(heldout)}  questions: {n_q}")
        print(f"deck fronts checked: {len(deck_fronts)}")
        print(f"leak threshold (Jaccard): {LEAK_THRESHOLD}")
        if violations:
            print(f"LEAKAGE FOUND ({len(violations)} violation(s)):")
            for v in violations:
                print(f"  - {v}")
        else:
            print("LEAKAGE CLEAN: no held-out question overlaps training deck")

    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description="Held-out eval leakage checker")
    ap.add_argument("--heldout", default=HELDOUT)
    args = ap.parse_args()
    violations = check(args.heldout)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
