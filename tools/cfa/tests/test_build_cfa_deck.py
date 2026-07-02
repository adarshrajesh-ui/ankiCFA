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
        # every card's note carries a los:: tag
        for cid in cids[:50]:
            note = col.get_card(cid).note()
            assert any(t.startswith("los::") for t in note.tags)
    finally:
        col.close()
        if os.path.exists(tmp):
            os.remove(tmp)
