# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the CFA Level II deck builder and its JSONL item files.

The validator/loader tests are pure-Python and need no built Anki. The
collection-build test is guarded by ``importorskip("anki")`` so it runs only
when pylib has been built.
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

REPO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
DECK_DIR = os.path.join(REPO, "cfa", "deck")
TOOLS_CFA = os.path.join(REPO, "tools", "cfa")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate_deck = _load("cfa_validate_deck", os.path.join(DECK_DIR, "validate_deck.py"))
build_cfa_deck = _load("cfa_build_deck", os.path.join(TOOLS_CFA, "build_cfa_deck.py"))


def test_item_files_pass_validator():
    count, errors = validate_deck.validate(DECK_DIR)
    assert errors == [], f"validator reported {len(errors)} problem(s): {errors[:5]}"
    assert count > validate_deck.MIN_CARDS


def test_loader_dedups_and_tags_are_los():
    items = build_cfa_deck.load_items(DECK_DIR)
    assert len(items) > 200
    # every tag is a los:: hierarchical tag
    assert all(i["los_tag"].startswith("los::") for i in items)
    # de-duplicated by front (case-insensitive)
    fronts = [i["front"].strip().lower() for i in items]
    assert len(fronts) == len(set(fronts))


def test_topic_weights_renormalize_to_one():
    items = build_cfa_deck.load_items(DECK_DIR)
    weights = build_cfa_deck.topic_weights_for(items)
    assert weights, "expected at least one topic weight"
    assert all(k.startswith("los::") for k in weights)
    assert abs(sum(weights.values()) - 1.0) < 1e-6
    # every topic present in the items has a weight
    present = {build_cfa_deck.los_prefix(i["los_tag"]) for i in items}
    assert present.issubset(set(weights))


def test_all_ten_level_ii_topics_present():
    # The authored deck must cover every base CFA Level II topic — including
    # fixed-income and derivatives, which the item glob previously missed.
    items = build_cfa_deck.load_items(DECK_DIR)
    present = {build_cfa_deck.los_prefix(i["los_tag"]) for i in items}
    missing = set(build_cfa_deck.BASE_TOPIC_WEIGHTS) - present
    assert not missing, f"missing authored topics: {sorted(missing)}"
    weights = build_cfa_deck.topic_weights_for(items)
    assert set(weights) == set(build_cfa_deck.BASE_TOPIC_WEIGHTS)


def test_render_source_line_names_topic_and_reading():
    item = {
        "front": "q",
        "back": "a",
        "topic": "Fixed Income",
        "los_tag": "los::fixed-income::term-structure-forward-rates",
        "source": "authored",
        "license": "authored-original",
    }
    line = build_cfa_deck.render_source_line(item)
    assert line.startswith("Source:")
    assert "CFA Level II" in line
    assert "Fixed Income" in line
    # The specific reading is named, derived from the los:: tag (hyphens -> spaces).
    assert "term structure forward rates" in line


def test_back_with_source_is_additive_and_preserves_content():
    item = {
        "front": "q",
        "back": "The estimated slope coefficient.",
        "topic": "Quantitative Methods",
        "los_tag": "los::quant::simple-linear-regression",
        "source": "authored",
        "license": "authored-original",
    }
    back = build_cfa_deck.back_with_source(item)
    # Authored content is preserved verbatim; the named source is appended AFTER.
    assert back.startswith("The estimated slope coefficient.")
    assert build_cfa_deck.render_source_line(item) in back
    assert back.index("The estimated slope coefficient.") < back.index("Source:")
    assert "simple linear regression" in back


def test_classify_item_type_is_deterministic_and_closed():
    # Every authored item maps to exactly one of the closed type set.
    items = build_cfa_deck.load_items(DECK_DIR)
    types = {build_cfa_deck.classify_item_type(i) for i in items}
    assert types, "expected classified types"
    assert types.issubset(set(build_cfa_deck.ITEM_TYPES))
    # Deterministic: same item classifies the same way twice.
    for i in items[:20]:
        assert build_cfa_deck.classify_item_type(
            i
        ) == build_cfa_deck.classify_item_type(i)


def test_classify_item_type_examples():
    def item(front, back, los_tag):
        return {"front": front, "back": back, "los_tag": los_tag}

    # Ethics topic -> ethics-rule regardless of wording.
    assert (
        build_cfa_deck.classify_item_type(
            item(
                "Define material nonpublic information.",
                "info that ...",
                "los::ethics::mnpi",
            )
        )
        == "ethics-rule"
    )
    # A calculation prompt -> multi-step-calc.
    assert (
        build_cfa_deck.classify_item_type(
            item("Calculate the firm's WACC.", "WACC = 8.4%", "los::corp::wacc")
        )
        == "multi-step-calc"
    )
    # An equation-answer or "write the ..." prompt -> formula.
    assert (
        build_cfa_deck.classify_item_type(
            item(
                "Write the Cobb-Douglas production function.",
                "Y = A*K^a*L^(1-a)",
                "los::econ::growth",
            )
        )
        == "formula"
    )
    # A definitional prompt with no cues -> conceptual.
    assert (
        build_cfa_deck.classify_item_type(
            item(
                "What is intrinsic value?",
                "The value given full understanding.",
                "los::equity::val",
            )
        )
        == "conceptual"
    )


def test_bad_row_raises(tmp_path):
    bad = tmp_path / "items-bad.jsonl"
    bad.write_text('{"front": "q", "back": "a"}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        build_cfa_deck.load_items(str(tmp_path))


def test_build_into_collection():
    # Skips cleanly unless pylib has been built (the compiled backend + pb2
    # modules are present). Run `just cfa-deck-test` to build then run this.
    sys.path.insert(0, os.path.join(REPO, "out", "pylib"))
    sys.path.insert(0, os.path.join(REPO, "pylib"))
    Collection = pytest.importorskip("anki.collection").Collection

    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "gnhf-cfa-deck-test.anki2")
    if os.path.exists(tmp):
        os.remove(tmp)
    added = build_cfa_deck.build(tmp, apkg=None)
    assert added > 200

    col = Collection(tmp)
    try:
        deck_id = col.decks.id("CFA Level II")
        cids = col.decks.cids(deck_id)
        assert len(cids) > 200
        # every card's note carries a los:: tag AND a type:: content-type tag
        for cid in cids[:50]:
            note = col.get_card(cid).note()
            los = next(t for t in note.tags if t.startswith("los::"))
            type_tags = [t for t in note.tags if t.startswith("type::")]
            assert len(type_tags) == 1
            assert type_tags[0].split("::", 1)[1] in build_cfa_deck.ITEM_TYPES
            # Every built study card carries a visible NAMED SOURCE (D1): the
            # CFA Level II topic + the specific reading, derived from its los tag.
            back = note["Back"]
            assert "Source: CFA Level II" in back
            reading = build_cfa_deck.reading_from_los(los)
            assert reading and reading in back
    finally:
        col.close()
        if os.path.exists(tmp):
            os.remove(tmp)
