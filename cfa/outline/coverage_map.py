#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A7 — CFA Level II coverage map (topic -> covered? -> %).

Renders the ten official CFA Level II topic areas
(``cfa/outline/level2_topics.json``) as a coverage map: for each topic, its
official exam-weight band, whether the authored deck (``cfa/deck/*.jsonl``)
carries cards for it (covered), and its share of the deck (card coverage %).

Everything here is REAL, deck-derived data — no simulation, so no SIMULATED
label. Card counts are read straight from the checked-in item files by their
``los::`` topic prefix, which is exactly the join key the scoring engine uses
(``pylib/anki/cfa.py`` / ``rslib/src/scheduler/cfa_scores.rs``). The renderer is
stdlib-only (a hand-rolled PNG encoder + a 5x7 bitmap font), so it runs offline
with no matplotlib and no built backend.

Usage:
    python3 cfa/outline/coverage_map.py [--png OUT] [--check-parity]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUTLINE = os.path.join(HERE, "level2_topics.json")
DECK_GLOB = os.path.join(REPO, "cfa", "deck", "*.jsonl")

# The canonical sorted topic list, mirrored in pylib/anki/cfa.py and
# rslib/src/scheduler/cfa_scores.rs. Kept here as a literal so this module has
# no dependency on a built backend; the parity test asserts it matches
# cfa.CANONICAL_TOPICS.
CANONICAL_TOPICS = [
    "los::altinv",
    "los::corp",
    "los::derivatives",
    "los::econ",
    "los::equity",
    "los::ethics",
    "los::fixed-income",
    "los::fra",
    "los::portmgmt",
    "los::quant",
]


# =============================================================================
# Data
# =============================================================================


def load_outline(path: str = OUTLINE) -> list[dict]:
    """The ten topic areas, ordered by ``order`` (CFA curriculum sequence)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data["topics"], key=lambda t: t["order"])


def los_prefix(los_tag: str) -> str:
    """The ``los::<topic>`` prefix (first two ``::`` segments) of a tag."""
    parts = los_tag.split("::")
    return "::".join(parts[:2]) if len(parts) >= 2 else los_tag


def deck_card_counts(deck_glob: str = DECK_GLOB) -> dict[str, int]:
    """Number of authored cards per ``los::`` topic prefix, from the deck."""
    counts: dict[str, int] = {}
    for path in glob.glob(deck_glob):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                tag = json.loads(line).get("los_tag", "")
                if tag.startswith("los::"):
                    counts[los_prefix(tag)] = counts.get(los_prefix(tag), 0) + 1
    return counts


def build_rows(
    outline: list[dict], counts: dict[str, int]
) -> tuple[list[dict], int]:
    """One row per topic with covered flag + card-coverage share of the deck."""
    total = sum(counts.get(t["tag"], 0) for t in outline)
    rows = []
    for t in outline:
        n = counts.get(t["tag"], 0)
        rows.append(
            {
                "name": t["name"],
                "tag": t["tag"],
                "cards": n,
                "covered": n > 0,
                "share": (n / total) if total else 0.0,
                "weight_low": t["weight_low"],
                "weight_high": t["weight_high"],
            }
        )
    return rows, total


# =============================================================================
# 5x7 bitmap font (uppercase + digits + a few symbols)
# =============================================================================

# Each glyph is 7 rows of 5-bit patterns (MSB = leftmost pixel).
_FONT: dict[str, list[int]] = {
    " ": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    "A": [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "B": [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    "C": [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    "D": [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
    "E": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    "F": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    "G": [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F],
    "H": [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "I": [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "J": [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    "K": [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    "L": [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    "M": [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    "N": [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
    "O": [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "P": [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    "Q": [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    "R": [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    "S": [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
    "T": [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    "U": [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "V": [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    "W": [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
    "X": [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    "Y": [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    "Z": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    "0": [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F],
    "3": [0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    "7": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    "%": [0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03],
    "-": [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],
    ".": [0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C],
    ":": [0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00],
    "&": [0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D],
    "/": [0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10],
    "(": [0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02],
    ")": [0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08],
    "–": [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],  # en dash -> hyphen
    "—": [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],  # em dash -> hyphen
}


class _Canvas:
    """Minimal RGB raster with a stdlib PNG encoder + 5x7 text."""

    def __init__(self, w: int, h: int, bg=(255, 255, 255)):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x: int, y: int, rgb) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i : i + 3] = bytes(rgb)

    def rect(self, x0, y0, x1, y1, rgb) -> None:
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.set(x, y, rgb)

    def frame(self, x0, y0, x1, y1, rgb) -> None:
        self.rect(x0, y0, x1, y0, rgb)
        self.rect(x0, y1, x1, y1, rgb)
        self.rect(x0, y0, x0, y1, rgb)
        self.rect(x1, y0, x1, y1, rgb)

    def text(self, x: int, y: int, s: str, rgb, scale: int = 2) -> int:
        """Draw ``s`` (uppercased) at (x, y); returns the x after the string."""
        cx = x
        for ch in s.upper():
            glyph = _FONT.get(ch, _FONT["-"] if ch.strip() else _FONT[" "])
            for ry, bits in enumerate(glyph):
                for rx in range(5):
                    if bits & (1 << (4 - rx)):
                        self.rect(
                            cx + rx * scale,
                            y + ry * scale,
                            cx + rx * scale + scale - 1,
                            y + ry * scale + scale - 1,
                            rgb,
                        )
            cx += 6 * scale
        return cx

    def png_bytes(self) -> bytes:
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)  # filter type 0 per scanline
            row = (y * self.w) * 3
            raw += self.px[row : row + self.w * 3]

        def chunk(tag: bytes, data: bytes) -> bytes:
            c = struct.pack(">I", len(data)) + tag + data
            return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        idat = zlib.compress(bytes(raw), 9)
        return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


# CFA brand-ish palette.
_INK = (23, 37, 66)
_MUTE = (120, 132, 156)
_COVERED = (24, 132, 92)
_UNCOVERED = (196, 64, 64)
_BAR = (46, 96, 176)
_BAR_BG = (228, 233, 242)
_HEADER_BG = (23, 37, 66)
_WHITE = (255, 255, 255)


def render_png(rows: list[dict], total: int, path: str) -> str:
    """Draw the coverage map to ``path`` (PNG). Returns ``path``."""
    W = 900
    row_h = 46
    top = 96
    H = top + row_h * len(rows) + 40
    c = _Canvas(W, H)

    # Header band + title.
    c.rect(0, 0, W - 1, 72, _HEADER_BG)
    c.text(24, 20, "CFA LEVEL II COVERAGE MAP", _WHITE, scale=3)
    sub = f"{len(rows)} OFFICIAL TOPIC AREAS  {total} AUTHORED CARDS"
    c.text(24, 78, sub, _MUTE, 2)

    x_status = 430
    x_bar = 520
    bar_w = 200

    for i, r in enumerate(rows):
        y = top + i * row_h
        if i % 2 == 0:
            c.rect(0, y - 4, W - 1, y + row_h - 8, (247, 249, 252))
        # Topic name (truncate to fit).
        name = r["name"]
        c.text(24, y, name[:32], _INK, 2)
        # Covered? status dot + label.
        dot = _COVERED if r["covered"] else _UNCOVERED
        c.rect(x_status, y + 2, x_status + 14, y + 16, dot)
        c.text(x_status + 22, y, "YES" if r["covered"] else "NO", dot, 2)
        # Coverage bar (share of deck) + percent.
        c.rect(x_bar, y + 2, x_bar + bar_w, y + 16, _BAR_BG)
        fill = int(bar_w * r["share"])
        if fill > 0:
            c.rect(x_bar, y + 2, x_bar + fill, y + 16, _BAR)
        pct = f"{r['share'] * 100:.1f}%"
        c.text(x_bar + bar_w + 12, y, pct, _INK, 2)
        # Official exam weight band under the name.
        wt = f"WEIGHT {int(r['weight_low'] * 100)}-{int(r['weight_high'] * 100)}%"
        c.text(24, y + 18, wt, _MUTE, 1)

    c.frame(0, 0, W - 1, H - 1, _MUTE)
    with open(path, "wb") as f:
        f.write(c.png_bytes())
    return path


# =============================================================================
# Report + CLI
# =============================================================================


def format_report(rows: list[dict], total: int, png_path: str) -> str:
    covered = sum(1 for r in rows if r["covered"])
    lines = [
        "CFA Level II — coverage map (topic -> covered? -> % of deck)",
        "REAL data: card counts read from cfa/deck/*.jsonl (no simulation).",
        "=" * 68,
        f"{'topic':<34}{'covered':>9}{'cards':>7}{'deck %':>9}{'exam wt':>10}",
        "-" * 68,
    ]
    for r in rows:
        wt = f"{int(r['weight_low'] * 100)}-{int(r['weight_high'] * 100)}%"
        lines.append(
            f"{r['name'][:33]:<34}{('yes' if r['covered'] else 'NO'):>9}"
            f"{r['cards']:>7}{r['share'] * 100:>8.1f}%{wt:>10}"
        )
    lines += [
        "-" * 68,
        f"topics covered: {covered}/{len(rows)}   total authored cards: {total}",
        f"coverage map PNG: {png_path}",
    ]
    return "\n".join(lines)


def check_parity() -> bool:
    """Outline tags (sorted) == CANONICAL_TOPICS. Returns True on parity."""
    outline = load_outline()
    outline_tags = sorted(t["tag"] for t in outline)
    return outline_tags == sorted(CANONICAL_TOPICS) == CANONICAL_TOPICS


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CFA Level II coverage map")
    ap.add_argument("--png", default=os.path.join(HERE, "coverage-map.png"))
    ap.add_argument(
        "--check-parity",
        action="store_true",
        help="assert the outline tags match the canonical topic list",
    )
    args = ap.parse_args(argv)

    if args.check_parity and not check_parity():
        print("PARITY FAIL: outline tags != CANONICAL_TOPICS", file=sys.stderr)
        return 1

    outline = load_outline()
    counts = deck_card_counts()
    rows, total = build_rows(outline, counts)
    png = render_png(rows, total, args.png)
    print(format_report(rows, total, png))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
