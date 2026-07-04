#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A3 — Memory-model calibration: Brier score, log loss, reliability chart.

WHAT THIS IS (and is NOT)
-------------------------
This measures how well-*calibrated* our recall-probability model is: when it
says "70% chance you recall this", does the learner actually recall it ~70% of
the time? Calibration is the property that matters for the honest Memory score
— a probability we show a student has to mean what it says.

DATA SOURCE. We would prefer a real ``revlog`` fixture (actual reviews with
their model-predicted recall probability at the time of the review). No such
real fixture exists in-repo, so we fall back to the *same* seeded synthetic
held-out reviews the rest of the eval harness uses (``run_eval.simulate``).
Every number printed by this tool is therefore labelled ``SIMULATED``. If a
real revlog JSONL (fields ``pred`` in [0,1] and ``outcome`` in {0,1}) is passed
via ``--revlog``, we use it instead and drop the SIMULATED label.

METRICS
-------
* Brier score  = mean((pred - outcome)^2)          — lower is better (0..1).
* Log loss     = -mean(y*ln p + (1-y)*ln(1-p))     — lower is better.
* Reliability  = per-bin (mean predicted, observed frequency, count); a
  perfectly calibrated model sits on the y=x diagonal. ECE (10-bin) summarises
  the total weighted gap from the diagonal.

The reliability chart is rendered to a PNG with a tiny dependency-free encoder
(no matplotlib): observed-vs-predicted points sized by bin count, the y=x
reference diagonal, and per-bin gap bars. Stdlib only; deterministic by seed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run_eval  # noqa: E402

DEFAULT_BINS = 10
# Clip probabilities away from {0,1} so log loss stays finite.
_EPS = 1e-12


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def brier_score(scores: list[float], labels: list[int]) -> float:
    """Mean squared error between predicted probability and 0/1 outcome."""
    n = len(scores)
    if n == 0:
        return float("nan")
    return sum((s - y) ** 2 for s, y in zip(scores, labels)) / n


def log_loss(scores: list[float], labels: list[int]) -> float:
    """Mean negative log-likelihood (binary cross-entropy), clipped."""
    n = len(scores)
    if n == 0:
        return float("nan")
    total = 0.0
    for s, y in zip(scores, labels):
        p = min(1.0 - _EPS, max(_EPS, s))
        total += -(y * math.log(p) + (1 - y) * math.log(1.0 - p))
    return total / n


def reliability_bins(scores: list[float], labels: list[int],
                     bins: int = DEFAULT_BINS) -> list[dict]:
    """Per-bin reliability table: predicted confidence vs observed accuracy."""
    out = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [
            i for i, s in enumerate(scores)
            if (s >= lo and s < hi) or (b == bins - 1 and s == 1.0)
        ]
        if idx:
            conf = sum(scores[i] for i in idx) / len(idx)
            acc = sum(labels[i] for i in idx) / len(idx)
        else:
            conf = acc = float("nan")
        out.append({
            "lo": lo, "hi": hi, "count": len(idx),
            "confidence": conf, "accuracy": acc,
        })
    return out


def ece_from_bins(table: list[dict], total: int) -> float:
    """Expected calibration error from a reliability table."""
    if total == 0:
        return float("nan")
    e = 0.0
    for row in table:
        if row["count"]:
            e += (row["count"] / total) * abs(row["accuracy"] - row["confidence"])
    return e


def compute(scores: list[float], labels: list[int],
            bins: int = DEFAULT_BINS) -> dict:
    table = reliability_bins(scores, labels, bins)
    return {
        "n": len(scores),
        "bins": bins,
        "brier": brier_score(scores, labels),
        "log_loss": log_loss(scores, labels),
        "ece": ece_from_bins(table, len(scores)),
        "base_rate": (sum(labels) / len(labels)) if labels else float("nan"),
        "mean_pred": (sum(scores) / len(scores)) if scores else float("nan"),
        "reliability": table,
    }


# --------------------------------------------------------------------------- #
# Minimal dependency-free PNG encoder (truecolor RGB, no matplotlib)
# --------------------------------------------------------------------------- #
class _Canvas:
    def __init__(self, w: int, h: int, bg=(255, 255, 255)):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x: int, y: int, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(rgb)

    def rect(self, x0, y0, x1, y1, rgb):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.set(x, y, rgb)

    def line(self, x0, y0, x1, y1, rgb):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, rgb):
        for y in range(int(cy - r), int(cy + r) + 1):
            for x in range(int(cx - r), int(cx + r) + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, rgb)

    def png_bytes(self) -> bytes:
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)  # filter type 0 per scanline
            row = (y * self.w) * 3
            raw += self.px[row:row + self.w * 3]

        def chunk(tag: bytes, data: bytes) -> bytes:
            c = struct.pack(">I", len(data)) + tag + data
            return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        idat = zlib.compress(bytes(raw), 9)
        return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) \
            + chunk(b"IEND", b"")


def render_reliability_png(metrics: dict, path: str, simulated: bool) -> str:
    """Draw the reliability diagram to ``path`` (PNG). Returns ``path``."""
    W = H = 460
    M = 60  # margin -> plot area is a square
    c = _Canvas(W, H)
    ax0x, ax0y = M, H - M          # origin (bottom-left)
    ax1x, ax1y = W - M, M          # top-right
    plot_w = ax1x - ax0x
    plot_h = ax0y - ax1y

    def px(v):  # data x in [0,1] -> pixel
        return ax0x + v * plot_w

    def py(v):  # data y in [0,1] -> pixel
        return ax0y - v * plot_h

    grey = (210, 210, 210)
    axis = (40, 40, 40)
    diag = (150, 150, 150)
    barc = (232, 168, 120)   # gap bars (warm)
    pt = (30, 90, 180)       # calibration points (blue)

    # gridlines every 0.2
    for g in range(0, 6):
        v = g / 5.0
        c.line(px(v), ax1y, px(v), ax0y, grey)
        c.line(ax0x, py(v), ax1x, py(v), grey)
    # axes
    c.line(ax0x, ax0y, ax1x, ax0y, axis)
    c.line(ax0x, ax0y, ax0x, ax1y, axis)
    # perfect-calibration diagonal y = x
    c.line(px(0), py(0), px(1), py(1), diag)

    total = metrics["n"]
    bins = metrics["bins"]
    bw = plot_w / bins
    for row in metrics["reliability"]:
        if not row["count"]:
            continue
        conf, acc = row["confidence"], row["accuracy"]
        # gap bar: from diagonal (perfect) up/down to observed accuracy
        mid = (row["lo"] + row["hi"]) / 2.0
        bx = px(mid)
        c.rect(bx - bw * 0.28, min(py(acc), py(mid)),
               bx + bw * 0.28, max(py(acc), py(mid)), barc)
        # point sized by bin population
        frac = row["count"] / total if total else 0.0
        r = 2 + int(round(6 * math.sqrt(frac)))
        c.disc(px(conf), py(acc), r, pt)

    # tick marks at 0 / 0.5 / 1 on both axes
    for v in (0.0, 0.5, 1.0):
        c.line(px(v), ax0y, px(v), ax0y + 5, axis)
        c.line(ax0x - 5, py(v), ax0x, py(v), axis)

    # a small SIMULATED watermark band along the top when synthetic
    if simulated:
        c.rect(M, 8, M + 96, 20, (250, 224, 190))
        c.rect(M, 8, M + 96, 9, (210, 140, 60))       # top edge accent
        c.rect(M, 19, M + 96, 20, (210, 140, 60))     # bottom edge accent

    with open(path, "wb") as fh:
        fh.write(c.png_bytes())
    return path


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def load_revlog(path: str) -> tuple[list[float], list[int]]:
    scores: list[float] = []
    labels: list[int] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            scores.append(float(row["pred"]))
            labels.append(int(row["outcome"]))
    return scores, labels


def _fmt(metrics: dict, simulated: bool, chart_path: str) -> str:
    tag = "SIMULATED" if simulated else "REAL revlog"
    lines = [
        f"CFA memory-model calibration  [{tag}]",
        "-" * 60,
        f"reviews scored      : {metrics['n']}",
        f"base rate (recall)  : {metrics['base_rate']:.4f}",
        f"mean prediction     : {metrics['mean_pred']:.4f}",
        "",
        f"Brier score  (↓)   : {metrics['brier']:.4f}",
        f"Log loss     (↓)   : {metrics['log_loss']:.4f}",
        f"ECE (10-bin) (↓)   : {metrics['ece']:.4f}",
        "",
        "Reliability table (predicted confidence -> observed recall):",
        f"  {'bin':>10}  {'n':>7}  {'pred':>7}  {'obs':>7}  {'gap':>7}",
    ]
    for row in metrics["reliability"]:
        rng = f"{row['lo']:.1f}-{row['hi']:.1f}"
        if row["count"]:
            gap = abs(row["accuracy"] - row["confidence"])
            lines.append(
                f"  {rng:>10}  {row['count']:>7}  "
                f"{row['confidence']:>7.3f}  {row['accuracy']:>7.3f}  "
                f"{gap:>7.3f}"
            )
        else:
            lines.append(f"  {rng:>10}  {0:>7}  {'-':>7}  {'-':>7}  {'-':>7}")
    lines += ["", f"reliability chart   : {chart_path}"]
    if simulated:
        lines += [
            "",
            "NOTE: SIMULATED — synthetic held-out reviews (no real exam data).",
            "      Numbers validate the model math + metric code, not real-world",
            "      calibration. Pass --revlog with real reviews to drop this.",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CFA memory-model calibration")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--learners", type=int, default=run_eval.DEFAULT_LEARNERS)
    ap.add_argument("--bins", type=int, default=DEFAULT_BINS)
    ap.add_argument("--revlog", default=None,
                    help="real revlog JSONL (fields pred, outcome); "
                         "omit to use the SIMULATED held-out cohort")
    ap.add_argument("--png", default=os.path.join(HERE, "calibration.png"))
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    args = ap.parse_args(argv)

    if args.revlog:
        scores, labels = load_revlog(args.revlog)
        simulated = False
    else:
        sim = run_eval.simulate(seed=args.seed, learners=args.learners)
        scores, labels = sim["scores"], sim["labels"]
        simulated = True

    metrics = compute(scores, labels, bins=args.bins)
    chart = render_reliability_png(metrics, args.png, simulated)

    if args.json:
        payload = {k: v for k, v in metrics.items()}
        payload["simulated"] = simulated
        payload["chart"] = chart
        print(json.dumps(payload, indent=2))
    else:
        print(_fmt(metrics, simulated, chart))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
