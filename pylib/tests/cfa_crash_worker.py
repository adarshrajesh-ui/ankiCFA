# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Standalone review worker for the CFA crash-robustness test.

Run as a subprocess against a real collection path; it opens the collection and
answers cards in a tight loop, committing a real review (revlog + card state)
to disk on every iteration, until the parent SIGKILLs it. It writes a marker
file once the collection is open and the first review has committed, so the
parent knows kills will land *mid-review* rather than during startup.

Deliberately NOT prefixed ``test_`` so pytest never collects it. It is invoked
only via ``subprocess`` from ``test_cfa_crash_robustness.py``.
"""

from __future__ import annotations

import sys

from anki.collection import Collection


def _add_fresh_card(col: Collection, seq: int) -> None:
    """Add a brand-new note so the review queue is never permanently empty.

    A freshly added card is immediately in the new queue, which guarantees the
    worker keeps committing real reviews no matter how the existing cards have
    been scheduled into the future by earlier rounds."""
    nt = col.models.by_name("Basic")
    deck = col.decks.get_current_id()
    note = col.new_note(nt)
    note["Front"] = f"crash-refill-{seq}"
    note["Back"] = "answer"
    note.tags = ["los::topica::r1"]
    col.add_note(note, deck)


def _answer_one(col: Collection) -> bool:
    """Answer the next queued card Good; return False if the queue is empty."""
    card = col.sched.getCard()
    if card is None:
        return False
    col.sched.answerCard(card, 3)  # Good
    return True


def main(path: str, marker: str) -> None:
    col = Collection(path)
    wrote_marker = False
    seq = 0
    while True:
        if not _answer_one(col):
            # Ran dry — mint a fresh new card so the loop keeps writing reviews.
            _add_fresh_card(col, seq)
            seq += 1
            continue
        if not wrote_marker:
            # One real review has now committed to disk; tell the parent it is
            # safe (and meaningful) to start killing us.
            with open(marker, "w") as fh:
                fh.write("ready")
            wrote_marker = True


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
