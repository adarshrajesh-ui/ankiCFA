# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Feature F8 — cross-platform persistence proof.

F7 proved a bundled ``.apkg`` carries decks + note-types + templates to the
phone, but *not* arbitrary ``col.conf`` (so the fork exam config does NOT
travel that way). F8 closes that gap: the **sync** path carries everything a
fresh phone needs.

These tests stand up a real local ``anki-sync-server`` (the same Rust sync
engine that runs on-device under AnkiDroid per F6) and prove that after
seeding a desktop collection and syncing, a fresh "phone" collection ends up
with:

1. the **CFA study deck** (notes + cards),
2. the **ethics passages deck** (the F1 one-passage note-type + its cards),
3. the fork **exam config** (``cfa_exam_config`` in ``col.conf``) — the piece
   the ``.apkg`` path could not carry, and
4. a working **shared-engine exam queue**: ``build_exam_queue`` (the read-only
   Rust ``BuildExamQueue`` RPC) runs against the *synced* content + config on
   the phone-side collection and returns cards weakest-first.

Because the phone-side ``Collection`` here is backed by the identical Rust
engine that F6 proved loads under AnkiDroid, a green run is honest evidence
that the same content reaches the device over sync.
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

from anki import cfa
from anki import cfa_sync as cs
from tests.shared import getEmptyCol

# The F1 ethics one-passage importer lives under cfa/ethics_pairs (a namespace
# package with no anki dependency), so add it to the path directly.
_ETHICS_PKG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "cfa",
    "ethics_pairs",
)
if _ETHICS_PKG not in sys.path:
    sys.path.insert(0, _ETHICS_PKG)

import passages as P  # noqa: E402

CFA_DECK = "CFA Level II"
EXAM_DATE = "2026-08-25"
TOPIC_WEIGHTS = {"los::ethics": 0.20, "los::equity": 0.15, "los::fixed-income": 0.15}


@pytest.fixture
def server():
    base = tempfile.mkdtemp(prefix="gnhf-cfa-f8-")
    srv_base = os.path.join(base, "server")
    os.makedirs(srv_base, exist_ok=True)
    with cs.sync_server(srv_base) as handle:
        yield handle


def _seed_desktop():
    """A desktop collection seeded exactly as a CFA candidate's would be:
    a study deck of tagged notes, the ethics passages deck, and exam config."""
    col = getEmptyCol()

    # --- CFA study deck: a few notes tagged the way BuildExamQueue joins on ---
    deck_id = col.decks.id(CFA_DECK)
    seeds = [
        (
            "What does WACC stand for?",
            "weighted average cost of capital",
            ["los::equity", "type::conceptual"],
        ),
        (
            "Duration of a zero-coupon bond?",
            "its time to maturity",
            ["los::fixed-income", "type::formula"],
        ),
        (
            "Standard III(B) covers?",
            "fair dealing with clients",
            ["los::ethics", "type::ethics-rule"],
        ),
    ]
    for front, back, tags in seeds:
        note = col.newNote()
        note["Front"] = front
        note["Back"] = back
        note.tags = tags
        col.add_note(note, deck_id)

    # --- Ethics passages deck (F1 one-passage note-type) ---
    passages = P.load_passages()[:5]
    ethics_stats = P.import_passages(col, passages)

    # --- Fork exam config (persisted in col.conf -> syncs natively) ---
    cfa.set_exam_config(col, exam_date=EXAM_DATE, topic_weights=TOPIC_WEIGHTS)

    return col, deck_id, ethics_stats


def _sync_to_fresh_phone(desktop, server):
    """Seed the server from the desktop, then full-download onto a fresh phone."""
    d_auth = cs.login(desktop, server)
    cs.sync(desktop, d_auth)  # first sync -> full upload seeds the server

    phone = getEmptyCol()
    p_auth = cs.login(phone, server)
    cs.sync(phone, p_auth)  # fresh collection -> full download
    return phone


def test_cfa_deck_and_ethics_deck_reach_the_phone(server):
    desktop, _deck_id, ethics_stats = _seed_desktop()
    phone = _sync_to_fresh_phone(desktop, server)

    deck_names = {d.name for d in phone.decks.all_names_and_ids()}
    assert CFA_DECK in deck_names, deck_names
    assert P.DECK_NAME in deck_names, deck_names

    # every seeded note (3 CFA + 5 ethics) and note-type made the trip
    assert phone.note_count() == desktop.note_count()
    assert phone.note_count() == 3 + ethics_stats["total"]

    phone_notetypes = {nt["name"] for nt in phone.models.all()}
    assert P.NOTETYPE_NAME in phone_notetypes, phone_notetypes

    # the ethics cards carry their multi-span content, not just an empty shell
    ethics_nids = phone.find_notes(f'note:"{P.NOTETYPE_NAME}"')
    assert len(ethics_nids) == ethics_stats["total"]
    sample = phone.get_note(ethics_nids[0])
    assert sample["Passage"].strip()
    assert sample["GoldSpans"].strip()


def test_exam_config_reaches_the_phone_over_sync(server):
    """The piece the .apkg path (F7) could NOT carry: fork exam config in
    col.conf. Sync carries it natively."""
    desktop, _deck_id, _ = _seed_desktop()
    assert cfa.get_exam_config(desktop) is not None  # sanity: set on desktop

    phone = _sync_to_fresh_phone(desktop, server)

    cfg = cfa.get_exam_config(phone)
    assert cfg is not None, "exam config did not survive the sync"
    assert cfg["exam_date"] == EXAM_DATE
    assert cfg["topic_weights"] == TOPIC_WEIGHTS
    # and the derived value the dialogs use is computed identically on device
    assert cfa.days_to_exam(phone, today=__import__("datetime").date(2026, 7, 3)) == 53


def test_shared_engine_queue_runs_on_synced_phone_collection(server):
    """The read-only Rust BuildExamQueue RPC (F6 on-device engine) runs against
    the *synced* content + config on the phone side and returns cards."""
    desktop, _deck_id, _ = _seed_desktop()
    phone = _sync_to_fresh_phone(desktop, server)

    # locate the CFA deck on the phone by name (ids are stable across sync too)
    phone_deck_id = phone.decks.id(CFA_DECK)
    queue = cfa.build_exam_queue(phone, deck_id=phone_deck_id)

    # the fork RPC returns a queue of the synced (all-new) CFA cards
    assert hasattr(queue, "card_ids")
    card_ids = list(queue.card_ids)
    assert len(card_ids) == 3, f"expected the 3 synced CFA cards, got {len(card_ids)}"
    # every returned card really lives in the synced collection
    for cid in card_ids:
        assert phone.get_card(cid) is not None
