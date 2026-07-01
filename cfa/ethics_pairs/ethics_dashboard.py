# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render the per-cluster discrimination dashboard, and generate a standalone offline report.

``render_dashboard_html`` is PURE (no ``anki``) so it is reused by both the in-app add-on
(``__init__.py``) and this offline CLI, and can be unit-tested directly.

The dashboard is deliberately SEPARATE from Anki's FSRS memory statistics: it reports whether the
learner can discriminate near-identical cases within each confusable-Standard cluster, and it is
honest -- below a minimum number of attempts a cluster shows "Not enough data" rather than a number.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ethics_scoring import (  # noqa: E402
    DEFAULT_MIN_ATTEMPTS,
    DEFAULT_WINDOW,
    discrimination_by_cluster,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PAIRS = os.path.join(HERE, "pairs.jsonl")

# Honest framing (see README). This mechanism is evidence-grounded, NOT proven to raise exam scores.
DISCLAIMER = (
    "Evidence-grounded mechanism. Contrastive case-comparison is supported by learning-science "
    "research (Alfieri et al. 2013 meta-analysis, d≈0.50; Gentner et al. 2003 on adult "
    "professionals). That evidence is analogy-transferred to CFA ethics here — this dashboard is "
    "not a claim that the feature is proven to raise CFA exam scores."
)


def load_cluster_labels(path: str = DEFAULT_PAIRS) -> dict[str, str]:
    """Map cluster id -> human label, read from the bank (best-effort)."""
    labels: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                p = json.loads(line)
                labels.setdefault(p["cluster"], p.get("cluster_label", p["cluster"]))
    except OSError:
        pass
    return labels


def _card_html(score: dict, label: str) -> str:
    cluster = html.escape(label)
    if score["abstain"]:
        return f"""
        <div class="cluster abstain">
          <div class="cl-label">{cluster}</div>
          <div class="cl-point muted">Not enough data</div>
          <div class="cl-meta">{score["total_attempts"]} attempt(s) · need {score["min_attempts"]} to score</div>
        </div>"""
    lo, hi = score["range"]
    cov = score["coverage_pct"]
    return f"""
        <div class="cluster">
          <div class="cl-label">{cluster}</div>
          <div class="cl-point">{score["point"]:.0f}<span class="pct">%</span></div>
          <div class="cl-meta">95% CI {lo:.0f}–{hi:.0f}% · confidence: {html.escape(score["confidence"])}</div>
          <div class="cl-meta">{score["correct_in_window"]}/{score["attempts_in_window"]} correct in last {score["window"]}
            · {score["total_attempts"]} total</div>
          <div class="bar"><div class="fill" style="width:{cov:.0f}%"></div></div>
          <div class="cl-meta small">window coverage {cov:.0f}%</div>
        </div>"""


def render_dashboard_html(
    scores_by_cluster: dict[str, dict], labels: dict[str, str] | None = None
) -> str:
    """Build the full dashboard HTML from per-cluster score objects."""
    labels = labels or {}
    # stable order: known clusters first (by label), then any extras
    ordered = sorted(scores_by_cluster.items(), key=lambda kv: labels.get(kv[0], kv[0]))
    cards = "\n".join(_card_html(s, labels.get(c, c)) for c, s in ordered)
    if not cards:
        cards = '<div class="cluster abstain"><div class="cl-point muted">No pair attempts yet</div></div>'

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  body {{ font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; margin: 0; padding: 20px; color: #1c1c1c; }}
  h1 {{ font-size: 1.35rem; margin: 0 0 2px; }}
  .sub {{ color: #6a6a72; margin: 0 0 16px; font-size: .92rem; }}
  .sep {{ font-size: .8rem; color: #8a6d3b; background: #fcf3d9; border: 1px solid #f0e0a8;
          padding: 8px 12px; border-radius: 8px; margin-bottom: 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
  .cluster {{ border: 1px solid #e0e0e6; border-radius: 12px; padding: 16px; background: #fafafc; }}
  .cluster.abstain {{ background: #f4f4f6; }}
  .cl-label {{ font-weight: 700; font-size: .9rem; min-height: 2.4em; }}
  .cl-point {{ font-size: 2.4rem; font-weight: 800; color: #2e6fd6; }}
  .cl-point .pct {{ font-size: 1.1rem; font-weight: 700; }}
  .cl-point.muted {{ font-size: 1.2rem; color: #9a9aa2; }}
  .cl-meta {{ color: #666; font-size: .82rem; margin-top: 4px; }}
  .cl-meta.small {{ font-size: .74rem; }}
  .bar {{ height: 6px; background: #e6e6ec; border-radius: 4px; margin-top: 10px; overflow: hidden; }}
  .fill {{ height: 100%; background: #2e6fd6; }}
  .disclaimer {{ margin-top: 20px; color: #6a6a72; font-size: .8rem; line-height: 1.5;
                 border-top: 1px solid #e6e6ec; padding-top: 12px; }}
</style></head><body>
  <h1>CFA Ethics — Contrastive Discrimination</h1>
  <p class="sub">% of your last {DEFAULT_WINDOW} pair attempts that were fully correct, per confusable-Standard cluster.</p>
  <div class="sep">This is a discrimination score, separate from Anki's FSRS memory statistics. A pair
    counts as correct only if <b>both</b> conform/violate calls and the decisive fact are right.</div>
  <div class="grid">
  {cards}
  </div>
  <div class="disclaimer">{html.escape(DISCLAIMER)}</div>
</body></html>"""


def build_report(
    col, min_attempts: int = DEFAULT_MIN_ATTEMPTS, window: int = DEFAULT_WINDOW
) -> str:
    """Read the collection's revlog and return dashboard HTML."""
    import ethics_revlog  # local import so this module stays import-safe without anki

    records = ethics_revlog.read_attempts(col)
    scores = discrimination_by_cluster(
        records, min_attempts=min_attempts, window=window
    )
    return render_dashboard_html(scores, load_cluster_labels())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate the CFA Ethics discrimination dashboard (offline)."
    )
    ap.add_argument(
        "--col", required=True, help="path to collection.anki2 (must be closed in Anki)"
    )
    ap.add_argument(
        "--out", default=os.path.join(HERE, "dashboard.html"), help="output HTML path"
    )
    ap.add_argument("--min-attempts", type=int, default=DEFAULT_MIN_ATTEMPTS)
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    ap.add_argument("--open", action="store_true", help="open the report in a browser")
    args = ap.parse_args(argv)

    from anki.collection import Collection

    col = Collection(args.col)
    try:
        htmls = build_report(col, args.min_attempts, args.window)
    finally:
        col.close()
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(htmls)
    print(f"wrote dashboard -> {args.out}")
    if args.open:
        import webbrowser

        webbrowser.open("file://" + os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
