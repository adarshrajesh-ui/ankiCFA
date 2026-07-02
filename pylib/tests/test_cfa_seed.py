# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the CFA first-launch seeder (Feature 5).

A fresh collection seeded via ``tools/cfa/seed_collection.seed_collection`` must
end up with BOTH CFA study decks present (CFA Level II + CFA::Ethics Pairs) and
the exam config persisted, and re-running the seeder must be a no-op (idempotent,
never re-imports or clobbers existing cards).
"""

from __future__ import annotations

import os
import sys

from anki import cfa
from tests.shared import getEmptyCol

# Make the deck builder + ethics importer reachable when the test runs.
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _rel in ("tools/cfa", "cfa/ethics_pairs"):
    _full = os.path.join(_REPO, _rel)
    if _full not in sys.path:
        sys.path.insert(0, _full)

import seed_collection  # noqa: E402

MAIN_DECK = "CFA Level II"
ETHICS_DECK = "CFA::Ethics Pairs"


def _card_count(col, name: str) -> int:
    did = col.decks.id_for_name(name)
    assert did is not None, f"deck {name!r} missing"
    return col.decks.card_count(did, include_subdecks=True)


def test_fresh_collection_gets_both_decks():
    col = getEmptyCol()

    # Fresh profile: neither CFA deck exists yet.
    assert col.decks.id_for_name(MAIN_DECK) is None
    assert col.decks.id_for_name(ETHICS_DECK) is None

    summary = seed_collection.seed_collection(col, repo_root=_REPO)

    assert summary["main_seeded"] is True
    assert summary["ethics_seeded"] is True

    # Both decks present with cards.
    main_cards = _card_count(col, MAIN_DECK)
    ethics_cards = _card_count(col, ETHICS_DECK)
    assert main_cards > 200, f"expected the expanded deck, got {main_cards}"
    assert ethics_cards > 0

    # Exam config persisted.
    config = cfa.get_exam_config(col)
    assert config is not None
    assert config.get("exam_date")
    assert config.get("topic_weights")


def test_seeder_is_idempotent():
    col = getEmptyCol()

    seed_collection.seed_collection(col, repo_root=_REPO)
    main_first = _card_count(col, MAIN_DECK)
    ethics_first = _card_count(col, ETHICS_DECK)

    # Second run must not add or clobber anything.
    summary = seed_collection.seed_collection(col, repo_root=_REPO)
    assert summary["main_seeded"] is False
    assert summary["ethics_seeded"] is False
    assert summary.get("main_skipped")
    assert summary.get("ethics_skipped")

    assert _card_count(col, MAIN_DECK) == main_first
    assert _card_count(col, ETHICS_DECK) == ethics_first


def test_config_derived_when_main_deck_preexists_without_config():
    # A deck named "CFA Level II" already has cards but no exam config was
    # ever stored: the seeder must skip re-importing yet still persist a
    # config derived from the deck's topics.
    col = getEmptyCol()
    did = col.decks.id(MAIN_DECK)
    nt = col.models.by_name("Basic")
    note = col.new_note(nt)
    note["Front"] = "pre-existing"
    note["Back"] = "card"
    note.tags = ["los::ethics::standards"]
    col.add_note(note, did)
    assert cfa.get_exam_config(col) is None

    summary = seed_collection.seed_collection(col, repo_root=_REPO)

    assert summary["main_seeded"] is False
    assert summary["config_set"] is True
    assert _card_count(col, MAIN_DECK) == 1  # not re-imported
    config = cfa.get_exam_config(col)
    assert config is not None and config.get("topic_weights")
