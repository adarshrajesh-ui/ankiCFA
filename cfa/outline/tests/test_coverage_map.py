"""Tests for the A7 coverage map + the 10-topic outline (stdlib only)."""

from __future__ import annotations

import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTLINE_DIR = os.path.dirname(HERE)
sys.path.insert(0, OUTLINE_DIR)

import coverage_map as cm  # noqa: E402


def test_outline_has_ten_official_topics():
    outline = cm.load_outline()
    assert len(outline) == 10
    orders = [t["order"] for t in outline]
    assert orders == list(range(1, 11))  # 1..10, ordered
    # Every topic has a los:: tag, a name and a valid exam-weight band.
    for t in outline:
        assert t["tag"].startswith("los::")
        assert t["name"]
        assert 0.0 < t["weight_low"] <= t["weight_high"] < 1.0


def test_outline_tags_match_canonical_and_are_sorted():
    outline = cm.load_outline()
    tags = sorted(t["tag"] for t in outline)
    assert tags == cm.CANONICAL_TOPICS
    assert cm.CANONICAL_TOPICS == sorted(cm.CANONICAL_TOPICS)
    assert len(set(cm.CANONICAL_TOPICS)) == 10


def test_parity_with_pylib_canonical_topics_if_importable():
    # If the built backend is available, the module's literal list must equal
    # cfa.CANONICAL_TOPICS exactly (Python<->Rust<->outline single source).
    try:
        from anki import cfa  # type: ignore
    except Exception:
        return  # offline without a built backend: covered by the pylib suite
    assert cm.CANONICAL_TOPICS == cfa.CANONICAL_TOPICS


def test_check_parity_true():
    assert cm.check_parity() is True


def test_los_prefix_first_two_segments():
    assert cm.los_prefix("los::fixed-income::cds-basics") == "los::fixed-income"
    assert cm.los_prefix("los::derivatives::swaps-x") == "los::derivatives"
    assert cm.los_prefix("los::ethics") == "los::ethics"


def test_deck_counts_cover_all_ten_topics():
    counts = cm.deck_card_counts()
    for tag in cm.CANONICAL_TOPICS:
        assert counts.get(tag, 0) > 0, f"deck has no cards for {tag}"


def test_build_rows_shape_and_shares_sum_to_one():
    outline = cm.load_outline()
    counts = cm.deck_card_counts()
    rows, total = cm.build_rows(outline, counts)
    assert len(rows) == 10
    assert total == sum(counts.get(t, 0) for t in cm.CANONICAL_TOPICS)
    assert all(r["covered"] for r in rows)  # all ten covered by the deck
    assert abs(sum(r["share"] for r in rows) - 1.0) < 1e-9


def test_build_rows_marks_uncovered_topic():
    # A topic absent from the deck must render as not-covered with 0 cards.
    outline = cm.load_outline()
    counts = {t: 5 for t in cm.CANONICAL_TOPICS}
    counts.pop("los::derivatives")
    rows, _total = cm.build_rows(outline, counts)
    by = {r["tag"]: r for r in rows}
    assert by["los::derivatives"]["covered"] is False
    assert by["los::derivatives"]["cards"] == 0
    assert by["los::ethics"]["covered"] is True


def test_render_png_writes_valid_png(tmp_path):
    outline = cm.load_outline()
    counts = cm.deck_card_counts()
    rows, total = cm.build_rows(outline, counts)
    path = str(tmp_path / "map.png")
    cm.render_png(rows, total, path)
    with open(path, "rb") as f:
        head = f.read(8)
    assert head == b"\x89PNG\r\n\x1a\n"
    # IHDR width/height are sane.
    with open(path, "rb") as f:
        data = f.read()
    ihdr = data.index(b"IHDR")
    w, h = struct.unpack(">II", data[ihdr + 4 : ihdr + 12])
    assert w == 900 and h > 100


def test_main_exits_zero_and_reports(tmp_path, capsys):
    png = str(tmp_path / "cov.png")
    rc = cm.main(["--png", png, "--check-parity"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "coverage map" in out.lower()
    assert "topics covered: 10/10" in out
    assert os.path.exists(png)


def test_font_covers_every_topic_name_character():
    outline = cm.load_outline()
    for t in outline:
        for ch in t["name"].upper():
            assert ch in cm._FONT, f"font missing glyph for {ch!r}"
