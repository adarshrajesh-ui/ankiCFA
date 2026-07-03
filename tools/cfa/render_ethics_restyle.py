#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render before/after PROOF of the CFA one-passage ethics card restyle.

Screenshots BOTH sides of the real card (the live ``passage_front.html`` /
``passage_back.html`` + ``style.css``) with headless Chrome so the web restyle
can be compared honestly:

* ``ethics-restyle-<tag>-front.png`` — the fresh FRONT (question) state: the
  cluster over-line, the serif question, the reading passage, the verdict
  buttons, the highlight step and the primary CTA.
* ``ethics-restyle-<tag>-back.png``  — the BACK (answer) state after a genuine,
  fully-correct attempt. The back reads its grade from ``localStorage`` — a seed
  ``<script>`` writes a completed ``cfaEthics:pending`` payload BEFORE the back
  template's own script runs, so the governing Standard + per-span rationale
  reveal renders exactly as it does in the app.

Purely presentational: this reads the templates/CSS as-is and substitutes the
same way the importer does (``html.escape``). No collection, no Anki build.

Usage:
    out/pyenv/bin/python tools/cfa/render_ethics_restyle.py --tag before
    out/pyenv/bin/python tools/cfa/render_ethics_restyle.py --tag after
"""

from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PKG = os.path.join(REPO, "cfa", "ethics_pairs")
TEMPLATES = os.path.join(PKG, "templates")
OUT_DIR = os.path.join(REPO, "cfa", "ui", "reference", "app")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def load_item(item_id: str) -> dict:
    with open(os.path.join(PKG, "passages.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                if r["item_id"] == item_id:
                    return r
    raise SystemExit(f"item {item_id} not found")


def _read(name: str) -> str:
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
        return f.read()


def _page(css: str, body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>body{{background:#fff;margin:24px;}}\n{css}</style></head>"
        f"<body class='card'>{body}</body></html>"
    )


def render_front(item: dict, css: str) -> str:
    front = _read("passage_front.html")
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
    for k, v in subs.items():
        front = front.replace(k, v)
    return _page(css, front)


def render_back(item: dict, css: str) -> str:
    """Back template with a seeded, fully-correct completed attempt in localStorage."""
    back = _read("passage_back.html").replace(
        "{{ItemId}}", html.escape(item["item_id"], quote=False)
    )
    cluster = f"cluster::{item['cluster']}"
    spans = [
        {
            "phrase": g["phrase"],
            "rationale": g["rationale"],
            "tier": "full",
            "matched": True,
        }
        for g in item["gold_spans"]
    ]
    pending = {
        "itemId": item["item_id"],
        "cluster": cluster,
        "correct": True,
        "completed": True,
        "answerVerdict": item["verdict"],
        "verdictOK": True,
        "highlight": "correct",
        "found": len(spans),
        "near": 0,
        "total": len(spans),
        "standard": item["standard"],
        "rationale": item["rationale"],
        "spans": spans,
    }
    seed = (
        "<script>try{localStorage.setItem('cfaEthics:pending',"
        + json.dumps(json.dumps(pending, ensure_ascii=False))
        + ");}catch(e){}</script>"
    )
    return _page(css, seed + back)


def shoot(html_text: str, png_path: str, w: int, h: int) -> None:
    with tempfile.TemporaryDirectory() as d:
        html_path = os.path.join(d, "card.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_text)
        subprocess.run(
            [
                CHROME,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=2",
                f"--window-size={w},{h}",
                f"--screenshot={png_path}",
                f"file://{html_path}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    print(f"wrote {png_path}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="after", choices=["before", "after"])
    ap.add_argument("--item", default="PSG-17")
    ap.add_argument("--front-size", default="1000,760")
    ap.add_argument("--back-size", default="1000,600")
    args = ap.parse_args(argv)

    if not os.path.exists(CHROME):
        raise SystemExit(f"Chrome not found at {CHROME}")
    os.makedirs(OUT_DIR, exist_ok=True)
    item = load_item(args.item)
    css = _read("style.css")

    fw, fh = (int(x) for x in args.front_size.split(","))
    bw, bh = (int(x) for x in args.back_size.split(","))
    shoot(
        render_front(item, css),
        os.path.join(OUT_DIR, f"ethics-restyle-{args.tag}-front.png"),
        fw,
        fh,
    )
    shoot(
        render_back(item, css),
        os.path.join(OUT_DIR, f"ethics-restyle-{args.tag}-back.png"),
        bw,
        bh,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
