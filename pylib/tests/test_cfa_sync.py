# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for CFA two-way sync (Feature 9).

Stands up a real local ``anki-sync-server`` and drives a desktop <-> phone
round-trip through Anki's own sync engine:

* a review made on the desktop shows up on the phone after a sync (forward);
* a review made on the phone shows up on the desktop (reverse);
* when the *same* card is reviewed on both devices offline, the collections
  converge, both reviews persist in the revlog (no lost / double-counted
  reviews), and the card's final state reflects the **more-recent** review.

Plus pure-unit coverage of the documented conflict rule.
"""

from __future__ import annotations

import os
import tempfile
import time

import pytest

from anki import cfa_sync as cs
from tests.shared import getEmptyCol

# --------------------------------------------------------------------------
# Pure conflict-rule tests (no server / no build required)
# --------------------------------------------------------------------------


def test_conflict_rule_more_recent_wins():
    early = cs.ReviewEvent(card_id=1, reviewed_at_ms=1000, ease=1, source="desktop")
    late = cs.ReviewEvent(card_id=1, reviewed_at_ms=2000, ease=4, source="phone")
    assert cs.resolve_review_conflict(early, late) is late
    # order of arguments must not matter
    assert cs.resolve_review_conflict(late, early) is late


def test_conflict_rule_tie_is_deterministic():
    a = cs.ReviewEvent(card_id=1, reviewed_at_ms=1000, ease=2)
    b = cs.ReviewEvent(card_id=1, reviewed_at_ms=1000, ease=4)
    # identical timestamps (unreachable in practice) resolve the same way
    # regardless of argument order
    assert cs.resolve_review_conflict(a, b) is cs.resolve_review_conflict(b, a)
    assert cs.resolve_review_conflict(a, b) is b


def test_conflict_rule_rejects_cross_card():
    a = cs.ReviewEvent(card_id=1, reviewed_at_ms=1000, ease=2)
    b = cs.ReviewEvent(card_id=2, reviewed_at_ms=2000, ease=4)
    with pytest.raises(ValueError):
        cs.resolve_review_conflict(a, b)


# --------------------------------------------------------------------------
# Live round-trip against a real sync server
# --------------------------------------------------------------------------


def _review(col, cid: int, ease: int) -> None:
    # Settle first so this review's collection `mod` lands in a strictly later
    # millisecond than the preceding sync. Anki's incremental sync keys "does
    # the server have anything new?" off the collection modification time; in a
    # fast test the setup sync, a review, and the next sync can all share one ms
    # tick, so the receiving device's cached server-mod anchor collides with the
    # server's new mod and it reports NO_CHANGES forever (extra sync rounds do
    # NOT help — verified). Spacing the review's mod out is the actual fix.
    time.sleep(0.05)
    card = col.get_card(cid)
    card.start_timer()
    col.sched.answerCard(card, ease)


@pytest.fixture
def server():
    base = tempfile.mkdtemp(prefix="gnhf-cfa-sync-")
    srv_base = os.path.join(base, "server")
    os.makedirs(srv_base, exist_ok=True)
    with cs.sync_server(srv_base) as handle:
        yield handle


def _paired_collections(server):
    """Two collections both synced to a shared server, one card in each."""
    desktop = getEmptyCol()
    note = desktop.newNote()
    note["Front"] = "CFA: what does WACC stand for?"
    note["Back"] = "weighted average cost of capital"
    desktop.addNote(note)
    cid = desktop.find_cards("")[0]

    d_auth = cs.login(desktop, server)
    cs.sync(desktop, d_auth)  # seeds the server (full upload)

    phone = getEmptyCol()
    p_auth = cs.login(phone, server)
    cs.sync(phone, p_auth)  # full download
    assert phone.card_count() == 1 and phone.note_count() == 1

    return desktop, d_auth, phone, p_auth, cid


def test_forward_review_desktop_to_phone(server):
    desktop, d_auth, phone, p_auth, cid = _paired_collections(server)
    assert cs.revlog_events(phone, cid) == []

    _review(desktop, cid, 3)
    cs.sync(desktop, d_auth)
    cs.sync(phone, p_auth)

    events = cs.revlog_events(phone, cid)
    assert len(events) == 1
    assert events[0].ease == 3


def test_reverse_review_phone_to_desktop(server):
    desktop, d_auth, phone, p_auth, cid = _paired_collections(server)

    _review(phone, cid, 2)
    cs.sync(phone, p_auth)
    cs.sync(desktop, d_auth)

    events = cs.revlog_events(desktop, cid)
    assert len(events) == 1
    assert events[0].ease == 2


def test_conflict_more_recent_wins_no_lost_or_double_reviews(server):
    desktop, d_auth, phone, p_auth, cid = _paired_collections(server)

    # Same card reviewed on both devices while offline. Phone reviews last,
    # so by the "more-recent wins" rule the phone's review must decide the
    # card's final state.
    _review(desktop, cid, 1)
    time.sleep(0.01)
    _review(phone, cid, 4)

    desktop_ms = cs.last_review_ms(desktop, cid)
    phone_ms = cs.last_review_ms(phone, cid)
    assert phone_ms is not None and desktop_ms is not None
    assert phone_ms > desktop_ms  # phone is the more-recent review

    # Desktop uploads first, then phone downloads+merges+uploads, then desktop
    # converges.
    cs.sync(desktop, d_auth)
    cs.sync(phone, p_auth)
    cs.sync(desktop, d_auth)

    d_events = cs.revlog_events(desktop, cid)
    p_events = cs.revlog_events(phone, cid)

    # Both distinct reviews survive on both devices...
    d_ids = [e.reviewed_at_ms for e in d_events]
    p_ids = [e.reviewed_at_ms for e in p_events]
    assert {desktop_ms, phone_ms} <= set(d_ids)
    assert {desktop_ms, phone_ms} <= set(p_ids)

    # ...with no double-counting (unique revlog ids) and no divergence.
    assert len(d_ids) == len(set(d_ids))
    assert sorted(d_ids) == sorted(p_ids)

    # More-recent review wins: the converged card's last review is the phone's.
    converged = cs.last_review_ms(desktop, cid)
    assert converged == cs.last_review_ms(phone, cid) == phone_ms

    # And the documented rule agrees with what the sync engine actually did.
    winner = cs.resolve_review_conflict(
        cs.ReviewEvent(
            card_id=cid, reviewed_at_ms=desktop_ms, ease=1, source="desktop"
        ),
        cs.ReviewEvent(card_id=cid, reviewed_at_ms=phone_ms, ease=4, source="phone"),
    )
    assert winner.reviewed_at_ms == converged


# --------------------------------------------------------------------------
# Increment 2: D4/D7 round-trip of BOTH an ethics card and a CFA-deck card,
# phone -> desktop and then reverse, asserting the revlog counts (and the exact
# revlog ids) match on both sides. This is the machine-checked half of the
# roundtrip.mp4 human proof.
# --------------------------------------------------------------------------


def _add_card(col, deck_name: str, front: str, back: str) -> int:
    did = col.decks.id(deck_name)
    note = col.new_note(col.models.by_name("Basic"))
    note["Front"] = front
    note["Back"] = back
    col.add_note(note, did)
    return col.find_cards(f"nid:{note.id}")[0]


def _two_deck_devices(server):
    """Desktop + phone sharing a server, with a CFA-deck card and an ethics card."""
    desktop = getEmptyCol()
    cfa_cid = _add_card(
        desktop,
        "CFA Level II",
        "What does WACC stand for?",
        "weighted average cost of capital",
    )
    eth_cid = _add_card(
        desktop,
        "CFA::Ethics Pairs",
        "Acting on an unreleased earnings figure: conform or violate?",
        "violate - Standard II(A)",
    )
    d_auth = cs.login(desktop, server)
    cs.sync(desktop, d_auth)  # seed the server (full upload)

    phone = getEmptyCol()
    p_auth = cs.login(phone, server)
    cs.sync(phone, p_auth)  # full download
    assert phone.card_count() == 2
    return desktop, d_auth, phone, p_auth, cfa_cid, eth_cid


def test_roundtrip_ethics_and_cfa_card_revlog_counts_match(server):
    desktop, d_auth, phone, p_auth, cfa_cid, eth_cid = _two_deck_devices(server)

    # ---- forward: review BOTH cards on the phone, then land them on desktop ----
    _review(phone, cfa_cid, 3)
    _review(phone, eth_cid, 1)
    cs.sync(phone, p_auth)
    cs.sync(desktop, d_auth)

    for cid in (cfa_cid, eth_cid):
        d_events = cs.revlog_events(desktop, cid)
        p_events = cs.revlog_events(phone, cid)
        # same number of reviews, and the exact same revlog ids on both sides:
        # no review lost, none duplicated.
        assert len(d_events) == len(p_events) == 1, cid
        assert [e.reviewed_at_ms for e in d_events] == [
            e.reviewed_at_ms for e in p_events
        ]

    # ---- reverse: review the CFA card on the desktop, land it on the phone ----
    _review(desktop, cfa_cid, 4)
    cs.sync(desktop, d_auth)
    cs.sync(phone, p_auth)

    d_events = cs.revlog_events(desktop, cfa_cid)
    p_events = cs.revlog_events(phone, cfa_cid)
    assert len(d_events) == len(p_events) == 2
    assert [e.reviewed_at_ms for e in d_events] == [e.reviewed_at_ms for e in p_events]

    # ---- whole-collection revlog matches on both sides, with no duplicate ids ----
    d_all = desktop.db.list("select id from revlog order by id")
    p_all = phone.db.list("select id from revlog order by id")
    assert d_all == p_all
    assert len(d_all) == len(set(d_all)) == 3  # 2 forward reviews + 1 reverse
