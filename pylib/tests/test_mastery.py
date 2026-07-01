# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Python-side test for the Rust `get_deck_mastery` backend method.

Exercises the generated protobuf binding end to end: the computation itself
lives in Rust (rslib/src/stats/mastery.rs); this asserts Python can call it and
receives the expected per-deck summary.
"""

from anki.consts import CARD_TYPE_NEW, CARD_TYPE_REV
from tests.shared import getEmptyCol


def _add_basic_note(col):
    note = col.newNote()
    note["Front"] = "front"
    note["Back"] = "back"
    col.addNote(note)
    return note.cards()[0]


def test_get_deck_mastery():
    col = getEmptyCol()

    # New, never-reviewed card.
    new_card = _add_basic_note(col)
    assert new_card.type == CARD_TYPE_NEW

    # Young review card (below the 21-day mastery threshold), perfect recall.
    young = _add_basic_note(col)
    young.type = CARD_TYPE_REV
    young.ivl = 5
    young.reps = 4
    young.lapses = 0
    col.update_card(young)

    # Mature review card (>= 21 days) with 2 lapses out of 10 reps.
    mature = _add_basic_note(col)
    mature.type = CARD_TYPE_REV
    mature.ivl = 40
    mature.reps = 10
    mature.lapses = 2
    col.update_card(mature)

    decks = col._backend.get_deck_mastery()
    default = next(d for d in decks if d.deck_id == 1)

    assert default.total_cards == 3
    # Only the interval-40 review card clears the 21-day threshold.
    assert default.mastered_count == 1
    # Reviewed cards: 4/4 = 1.0 and 8/10 = 0.8 -> mean 0.9; the new card has no
    # reps and is excluded from the average.
    assert abs(default.avg_recall - 0.9) < 1e-6
