#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render a standalone HTML page of the F1 one-passage card for a given item, for headless-Chrome
proof. Substitutes the real passage/verdict/gold-spans/standard/rationale into the card template the
SAME way the Anki importer does (html.escape), wraps it with the shared style.css, and writes it to
an output path. The generated page uses the exact front template JS (tap/drag multi-span selection +
deterministic grading), so driving it in a browser proves the real review flow end-to-end.

Usage:
    out/pyenv/bin/python tools/cfa/render_f1_passage.py --item PSG-17 --out proof/gnhf2/f1.html
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

from ethics_scoring import find_gold_spans  # noqa: E402


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


def render_html(item: dict) -> str:
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

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>body{{background:#fff;margin:24px;}}\n{css}</style></head>"
        f"<body class='card'>{body}</body></html>"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", default="PSG-17")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    item = load_item(args.item)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_html(item))

    # Print the gold-span token indices so a driver can tap the exact first/last words of each span.
    phrases = [s["phrase"] for s in item["gold_spans"]]
    runs = find_gold_spans(item["passage"], phrases)
    plan = [{"phrase": p, "lo": r[0], "hi": r[-1]} for p, r in zip(phrases, runs)]
    print(
        json.dumps(
            {
                "item": item["item_id"],
                "verdict": item["verdict"],
                "out": os.path.abspath(args.out),
                "spans": plan,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
