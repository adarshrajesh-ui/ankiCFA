#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render the F2 one-passage card WITH the semantic AI-grading bridge wired in,
for headless-Chrome proof.

It reuses the exact F1 front template + style, but injects a ``window.pycmd``
stub that answers ``cfaGradeEthics:`` the SAME way the real desktop bridge
(``aqt.cfa_ethics_ai``) does — by running the real ``ai_grading.grade_semantic``
and handing back its JSON. To keep the run offline and deterministic, the LLM is
mocked with a small oracle that returns a realistic semantic JSON; the grade the
page shows is therefore genuine ``grade_semantic`` output, not a hand-drawn blob.

The chosen item/selection is a SEMANTIC-WIN case: the learner clips the gold
phrase boundaries, so the card's own deterministic grade is under-scored, and
the injected AI feedback block upgrades it to the correct grade with an
explanation — exactly the value F2 adds on desktop.

Usage:
    out/pyenv/bin/python tools/cfa/render_f2_ai_grade.py --item PSG-01 --out proof/gnhf2/f2.html
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PKG = os.path.join(REPO, "cfa", "ethics_pairs")
sys.path.insert(0, PKG)
sys.path.insert(0, REPO)

from ai_grading import grade_semantic  # noqa: E402
from ethics_scoring import find_gold_spans  # noqa: E402

# Per-item semantic-win learner selections (clipped boundaries) + the oracle
# JSON a competent LLM would return for them.
SCENARIOS = {
    "PSG-01": {
        "judged": "unethical",
        "learner_spans": ["unreleased quarterly earnings figure", "sells the company"],
        "oracle": {
            "verdict_correct": True,
            "highlight_grade": "correct",
            "explanation": "You nailed both: the still-unreleased earnings figure is "
            "the MNPI, and selling the position is the prohibited trade on it.",
            "spans": [
                {
                    "phrase": "exact unreleased quarterly earnings figure",
                    "matched": True,
                    "note": "the precise nonpublic number",
                },
                {
                    "phrase": "sells the company out of her clients' portfolios",
                    "matched": True,
                    "note": "trading on the MNPI",
                },
            ],
        },
    },
}


def load_item(item_id: str) -> dict:
    path = os.path.join(PKG, "passages.jsonl")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                if r["item_id"] == item_id:
                    return r
    raise SystemExit(f"item {item_id} not found in {path}")


def render_html(item: dict, grade_result: dict) -> str:
    front = open(
        os.path.join(PKG, "templates", "passage_front.html"), encoding="utf-8"
    ).read()
    css = open(os.path.join(PKG, "templates", "style.css"), encoding="utf-8").read()

    gold_json = json.dumps(
        [
            {"phrase": s["phrase"], "rationale": s["rationale"]}
            for s in item["gold_spans"]
        ],
        ensure_ascii=False,
    )
    subs = {
        "{{ItemId}}": html.escape(item["item_id"], quote=False),
        "{{Passage}}": html.escape(item["passage"], quote=False),
        "{{Verdict}}": html.escape(item["verdict"], quote=False),
        "{{GoldSpans}}": html.escape(gold_json, quote=False),
        "{{Standard}}": html.escape(item["standard"], quote=False),
        "{{ClusterTag}}": f"cluster::{item['cluster']}",
        "{{Rationale}}": html.escape(item["rationale"], quote=False),
    }
    body = front
    for k, v in subs.items():
        body = body.replace(k, v)

    # pycmd stub: mirrors the desktop bridge — returns the precomputed real
    # grade_semantic JSON to the card's callback.
    stub = (
        "<script>window.pycmd = function (arg, cb) {"
        "  if (typeof arg === 'string' && arg.indexOf('cfaGradeEthics:') === 0 && cb) {"
        f"    cb({json.dumps(grade_result)});"
        "  }"
        "  return false;"
        "};</script>"
    )

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>body{{background:#fff;margin:24px;}}\n{css}</style>{stub}</head>"
        f"<body class='card'>{body}</body></html>"
    )


def _oracle_fn(oracle_json):
    def fn(**kwargs):
        return {
            "ok": True,
            "text": json.dumps(oracle_json),
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 120},
            "error": None,
            "purpose": kwargs.get("purpose", ""),
        }

    return fn


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", default="PSG-01")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    item = load_item(args.item)
    scen = SCENARIOS.get(args.item)
    if not scen:
        raise SystemExit(f"no semantic-win scenario defined for {args.item}")

    # Compute the REAL semantic grade the bridge would return (LLM mocked offline).
    grade_result = grade_semantic(
        item["passage"],
        item["verdict"],
        scen["judged"],
        item["gold_spans"],
        scen["learner_spans"],
        complete_fn=_oracle_fn(scen["oracle"]),
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_html(item, grade_result))

    # Emit the learner's clipped-span token ranges so a driver can tap them.
    runs = find_gold_spans(item["passage"], scen["learner_spans"])
    plan = [
        {"phrase": p, "lo": r[0], "hi": r[-1]}
        for p, r in zip(scen["learner_spans"], runs)
    ]
    print(
        json.dumps(
            {
                "item": item["item_id"],
                "judged": scen["judged"],
                "out": os.path.abspath(args.out),
                "learner_selection": plan,
                "deterministic_grade": grade_semantic(
                    item["passage"],
                    item["verdict"],
                    scen["judged"],
                    item["gold_spans"],
                    scen["learner_spans"],
                    complete_fn=lambda **k: {"ok": False, "error": "ai_off"},
                )["grade"],
                "ai_grade": grade_result["grade"],
                "ai_source": grade_result["source"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
