#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render a standalone HTML page of the CFA Ethics MINIMAL-PAIR card for headless-Chrome proof of a
FULL graded attempt.

Substitutes a real pair (pairs.jsonl) into the minimal-pair FRONT template the SAME way the Anki
importer does (html.escape), wraps it with the shared style.css, and — because a plain
``chrome --screenshot`` cannot drive the tap/judge/Check interaction — appends a tiny AUTO-DRIVER
script that programmatically performs a complete attempt on load (pick both conform/violate
verdicts, highlight the decisive span(s) in the violating vignette, click Check). With
``chrome --headless --virtual-time-budget`` the screenshot then captures the fully-graded reveal
(grade tier + per-span breakdown + governing Standard + rationale).

The interaction the driver runs is the REAL front-template JS (the shared multi-span grader), so the
screenshot is a genuine end-to-end attempt, not a mock-up.

Drive modes (``--mode``):
  * ``perfect``  — highlight every gold span exactly -> "Fully correct".
  * ``partial``  — highlight only the first gold span -> partial credit (Item 1 multi-span tier).
  * ``blank``    — render the fresh front only (no attempt); used for BEFORE shots.

Optionally injects a ``window.pycmd`` oracle stub (``--ai``) so the AI-feedback block renders (INC2
proof); the grade shown is real ``ai_grading.grade_semantic`` output with a mocked offline LLM.

Usage:
    out/pyenv/bin/python tools/cfa/render_pairs_attempt.py --pair SMD-01 --mode perfect \
        --out proof/friday/ethics/item1-after.html
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

from ethics_scoring import find_gold_spans  # noqa: E402


def load_pair(pair_id: str) -> dict:
    path = os.path.join(PKG, "pairs.jsonl")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                if r["pair_id"] == pair_id:
                    return r
    raise SystemExit(f"pair {pair_id} not found in {path}")


def _gold_spans_for(pair: dict) -> list[dict]:
    """The authored multi-span answer key on the violating vignette (falls back to legacy phrase)."""
    spans = pair.get("gold_spans")
    if isinstance(spans, list) and spans:
        return [
            {"phrase": s["phrase"], "rationale": s.get("rationale", "")} for s in spans
        ]
    return [{"phrase": pair["decisive_phrase"], "rationale": pair.get("rationale", "")}]


def _decisive_case(pair: dict) -> str:
    return "A" if pair["answer_a"] == "violate" else "B"


def render_html(pair: dict, mode: str, ai_result: dict | None) -> str:
    front = open(os.path.join(PKG, "templates", "front.html"), encoding="utf-8").read()
    css = open(os.path.join(PKG, "templates", "style.css"), encoding="utf-8").read()

    gold_spans = _gold_spans_for(pair)
    gold_json = json.dumps(gold_spans, ensure_ascii=False)
    subs = {
        "{{PairId}}": html.escape(pair["pair_id"], quote=False),
        "{{ClusterTag}}": f"cluster::{pair['cluster']}",
        "{{VignetteA}}": html.escape(pair["vignette_a"], quote=False),
        "{{VignetteB}}": html.escape(pair["vignette_b"], quote=False),
        "{{AnswerA}}": html.escape(pair["answer_a"], quote=False),
        "{{AnswerB}}": html.escape(pair["answer_b"], quote=False),
        "{{DecisiveFact}}": html.escape(pair.get("decisive_fact", ""), quote=False),
        "{{DecisivePhrase}}": html.escape(pair["decisive_phrase"], quote=False),
        "{{DecisivePhraseCase}}": html.escape(
            pair["decisive_phrase_case"], quote=False
        ),
        "{{GoldSpans}}": html.escape(gold_json, quote=False),
        "{{Standard}}": html.escape(pair["standard"], quote=False),
        "{{Rationale}}": html.escape(pair["rationale"], quote=False),
    }
    body = front
    for k, v in subs.items():
        body = body.replace(k, v)

    # Plan the driver's taps: the gold span index runs in the violating vignette.
    decisive_case = _decisive_case(pair)
    vign = pair["vignette_a"] if decisive_case == "A" else pair["vignette_b"]
    runs = find_gold_spans(vign, [s["phrase"] for s in gold_spans])
    span_ranges = [[r[0], r[-1]] for r in runs if r]
    if mode == "partial":
        span_ranges = span_ranges[:1]

    ai_stub = ""
    if ai_result is not None:
        ai_stub = (
            "<script>window.pycmd = function (arg, cb) {"
            "  if (typeof arg === 'string' && arg.indexOf('cfaGradeEthics:') === 0 && cb) {"
            f"    setTimeout(function(){{ cb({json.dumps(ai_result)}); }}, 30);"
            "  }"
            "  return false;"
            "};</script>"
        )

    driver = ""
    if mode in ("perfect", "partial"):
        driver = _driver_script(
            pair["answer_a"], pair["answer_b"], decisive_case, span_ranges
        )

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>body{{background:#fff;margin:24px;max-width:760px;}}\n{css}</style>{ai_stub}</head>"
        f"<body class='card'>{body}{driver}</body></html>"
    )


def _driver_script(
    answer_a: str, answer_b: str, decisive_case: str, span_ranges: list
) -> str:
    """A tiny on-load driver that performs a full attempt using the real card handlers."""
    cfg = json.dumps(
        {
            "answerA": answer_a,
            "answerB": answer_b,
            "decisiveCase": decisive_case,
            "spans": span_ranges,
        }
    )
    return (
        "<script>(function(){var CFG=" + cfg + ";"
        "function fire(el,type){var ev=new MouseEvent(type,{bubbles:true,cancelable:true,view:window});el.dispatchEvent(ev);}"
        "function tap(el){fire(el,'pointerdown');fire(el,'pointerup');fire(el,'click');}"
        "function run(){"
        "  var root=document.querySelector('.cfa-pair'); if(!root){return;}"
        "  ['A','B'].forEach(function(c){"
        "    var ans=c==='A'?CFG.answerA:CFG.answerB;"
        "    var btn=root.querySelector('.cfa-case[data-case=\"'+c+'\"] .cfa-judge-btn[data-j=\"'+ans+'\"]');"
        "    if(btn){tap(btn);}"
        "  });"
        "  var panel=root.querySelector('.cfa-case[data-case=\"'+CFG.decisiveCase+'\"]');"
        "  CFG.spans.forEach(function(rg){"
        "    var lo=panel.querySelector('.cfa-tok[data-i=\"'+rg[0]+'\"]');"
        "    var hi=panel.querySelector('.cfa-tok[data-i=\"'+rg[1]+'\"]');"
        "    if(lo){tap(lo);} if(hi){tap(hi);}"
        "  });"
        "  var check=root.querySelector('#cfa-check');"
        "  if(check&&!check.disabled){tap(check);}"
        "  setTimeout(dumpPayload,120);"  # after reveal persists the payload
        "}"
        "function dumpPayload(){"
        "  var pre=document.getElementById('cfa-emitted-payload');"
        "  if(!pre){pre=document.createElement('pre');pre.id='cfa-emitted-payload';pre.style.display='none';document.body.appendChild(pre);}"
        "  try{pre.textContent=localStorage.getItem('cfaEthics:pending')||'';}catch(e){pre.textContent='';}"
        "}"
        "if(document.readyState==='complete'||document.readyState==='interactive'){setTimeout(run,60);}"
        "else{document.addEventListener('DOMContentLoaded',function(){setTimeout(run,60);});}"
        "})();</script>"
    )


def _oracle_ai(pair: dict) -> dict:
    """Compute the REAL grade_semantic result with a mocked offline oracle LLM (INC2 proof)."""
    from ai_grading import grade_semantic

    gold_spans = _gold_spans_for(pair)
    decisive_case = _decisive_case(pair)
    vign = pair["vignette_a"] if decisive_case == "A" else pair["vignette_b"]
    learner = [s["phrase"] for s in gold_spans]
    oracle_json = {
        "verdict_correct": True,
        "highlight_grade": "correct",
        "explanation": "You identified the decisive evidence that makes this a violation.",
        "spans": [
            {"phrase": s["phrase"], "matched": True, "note": "the decisive fact"}
            for s in gold_spans
        ],
    }

    def fn(**kwargs):
        return {
            "ok": True,
            "text": json.dumps(oracle_json),
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 120},
            "error": None,
            "purpose": kwargs.get("purpose", ""),
        }

    return grade_semantic(
        vign,
        "violate",
        "violate",
        gold_spans,
        learner,
        complete_fn=fn,
        item_id=pair["pair_id"],
        standard=pair["standard"],
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="SMD-01")
    ap.add_argument(
        "--mode", choices=["perfect", "partial", "blank"], default="perfect"
    )
    ap.add_argument(
        "--ai",
        action="store_true",
        help="inject a pycmd oracle stub (AI-feedback block)",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    pair = load_pair(args.pair)
    ai_result = _oracle_ai(pair) if args.ai else None
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_html(pair, args.mode, ai_result))

    decisive_case = _decisive_case(pair)
    vign = pair["vignette_a"] if decisive_case == "A" else pair["vignette_b"]
    runs = find_gold_spans(vign, [s["phrase"] for s in _gold_spans_for(pair)])
    print(
        json.dumps(
            {
                "pair": pair["pair_id"],
                "mode": args.mode,
                "out": os.path.abspath(args.out),
                "decisive_case": decisive_case,
                "gold_span_ranges": [[r[0], r[-1]] for r in runs if r],
                "standard": pair["standard"],
                "ai": bool(args.ai and ai_result and ai_result.get("source") == "ai"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
