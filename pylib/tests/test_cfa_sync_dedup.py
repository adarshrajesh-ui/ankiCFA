# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Increment 3 + 5 sync correctness tests.

Increment 3 (flagship): when the *same* card is reviewed offline on both a
desktop and a phone, sync keeps **both** revlog rows (no lost reviews) but
per-(card, day) dedup must **not** inflate graded-review / give-up totals.

Increment 5: ``card.custom_data["cfaEthics"]`` round-trips through the real
sync server unchanged.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from anki import cfa
from anki import cfa_sync as cs
from tests.shared import getEmptyCol

# --------------------------------------------------------------------------
# Increment 3 helpers
# --------------------------------------------------------------------------


def _review(col, cid: int, ease: int) -> None:
    card = col.get_card(cid)
    card.start_timer()
    col.sched.answerCard(card, ease)


@pytest.fixture
def server():
    base = tempfile.mkdtemp(prefix="cfa-sync-dedup-")
    srv_base = os.path.join(base, "server")
    os.makedirs(srv_base, exist_ok=True)
    with cs.sync_server(srv_base) as handle:
        yield handle


def _paired_one_card(server):
    desktop = getEmptyCol()
    note = desktop.newNote()
    note["Front"] = "CFA sync dedup probe"
    note["Back"] = "answer"
    desktop.addNote(note)
    cid = desktop.find_cards("")[0]

    d_auth = cs.login(desktop, server)
    cs.sync(desktop, d_auth)

    phone = getEmptyCol()
    p_auth = cs.login(phone, server)
    cs.sync(phone, p_auth)
    assert phone.card_count() == 1
    return desktop, d_auth, phone, p_auth, cid


def test_offline_same_card_dual_review_revlog_distinct_not_inflated(server):
    """Flagship: two offline reviews of one card -> 2 revlog rows, dedup count 1."""
    desktop, d_auth, phone, p_auth, cid = _paired_one_card(server)

    _review(desktop, cid, 2)
    time.sleep(0.01)
    _review(phone, cid, 3)

    assert len(cs.revlog_events(desktop, cid)) == 1
    assert len(cs.revlog_events(phone, cid)) == 1

    cs.sync(desktop, d_auth)
    cs.sync(phone, p_auth)
    cs.sync(desktop, d_auth)

    d_events = cs.revlog_events(desktop, cid)
    p_events = cs.revlog_events(phone, cid)
    assert len(d_events) == len(p_events) == 2
    assert {e.reviewed_at_ms for e in d_events} == {e.reviewed_at_ms for e in p_events}
    assert len({e.reviewed_at_ms for e in d_events}) == 2  # distinct ids

    raw = cs.raw_graded_review_count(desktop)
    deduped = cs.deduped_graded_review_count(desktop)
    assert raw == 2, "both reviews must persist in revlog (no silent merge)"
    assert deduped == 1, "per-(card,day) dedup must NOT inflate give-up totals"

    # Integrated contract (D4): memory_score() now dedups per-(card, day) via the
    # shared engine, so the same card reviewed offline on two devices is NOT
    # double-counted toward give-up totals. Raw revlog rows are still preserved
    # (asserted above): no lost reviews, no inflated counts.
    score = cfa.memory_score(desktop)
    assert score.graded_reviews == deduped


def test_dedup_would_fail_if_naive_count_used_for_giveup(server):
    """Regression guard: if deduped == raw with two same-day reviews, test fails."""
    desktop, d_auth, phone, p_auth, cid = _paired_one_card(server)
    _review(desktop, cid, 1)
    time.sleep(0.01)
    _review(phone, cid, 4)
    cs.sync(desktop, d_auth)
    cs.sync(phone, p_auth)
    cs.sync(desktop, d_auth)

    raw = cs.raw_graded_review_count(desktop)
    deduped = cs.deduped_graded_review_count(desktop)
    assert raw >= 2
    assert deduped < raw, "same-card-same-day double review must not double-count for scoring"


def test_different_days_both_count(server):
    """Sanity: reviews on different collection days both count after dedup.

    Dedup is per-(card, collection-day): two reviews of one card on two
    *different* days must count as 2, never collapse to 1 (same-day dedup is
    covered by the tests above). This exercises the day-bucketing of
    ``deduped_graded_review_count`` directly.

    It deliberately does NOT re-sync a hand-edited revlog row: rewriting a
    revlog primary key via raw SQL does not bump ``usn``, so whether that edit
    survives a subsequent sync is nondeterministic (it can trigger a
    full-download that discards the local edit). That made this check racy
    without adding real sync coverage — same-card dual-device sync + dedup is
    already proven above.
    """
    desktop, d_auth, phone, p_auth, cid = _paired_one_card(server)
    _review(desktop, cid, 3)

    # Backdate that review 2 collection-days so the next one lands on a
    # different day bucket.
    rid = cs.revlog_events(desktop, cid)[0].reviewed_at_ms
    day_back_ms = int((desktop.crt - 2 * 86400) * 1000)
    desktop.db.execute("update revlog set id = ? where id = ?", day_back_ms, rid)

    # A second review "today" on the same card.
    _review(desktop, cid, 4)

    assert cs.raw_graded_review_count(desktop) == 2
    assert cs.deduped_graded_review_count(desktop) == 2  # two distinct days


# --------------------------------------------------------------------------
# Increment 5: custom_data round-trip
# --------------------------------------------------------------------------

_SAMPLE_ETHICS = {
    "pairId": "SMD-01",
    "itemId": "SMD-01",
    "cluster": "cluster::suitability-mnpi-diligence",
    "completed": True,
    "correct": True,
    "standard": "II(A) Material Nonpublic Information",
    "source": "fallback",
    "verdicts": {"A": {"judged": "violate", "answer": "violate", "ok": True}},
    "decisiveCase": "A",
    "highlight": "correct",
    "found": 2,
    "near": 0,
    "total": 2,
    "selectionIndices": [24, 25, 26],
    "spans": [{"phrase": "earnings figure", "tier": "full", "matched": True, "lo": 24, "hi": 28}],
}


def test_ethics_custom_data_roundtrips_through_sync_server(server):
    # Anki custom_data keys must be <= 8 bytes; use "cfaEthic" (8) not "cfaEthics" (9).
    ns = "cfaEthic"
    desktop = getEmptyCol()
    note = desktop.newNote()
    note["Front"] = "Ethics sync payload probe"
    note["Back"] = "violate"
    desktop.addNote(note)
    cid = desktop.find_cards("")[0]
    cs.merge_custom_data(desktop, cid, ns, cs.compact_ethics_payload(_SAMPLE_ETHICS))

    d_auth = cs.login(desktop, server)
    cs.sync(desktop, d_auth)

    phone = getEmptyCol()
    p_auth = cs.login(phone, server)
    cs.sync(phone, p_auth)

    got = cs.read_custom_data_namespace(phone, cid, ns)
    assert got is not None
    assert got["id"] == "SMD-01"
    assert got["hl"] == "correct"
    assert got["src"] == "fb"

    # Mutate on phone, sync back to desktop.
    got["src"] = "ai"
    cs.merge_custom_data(phone, cid, ns, got)
    cs.sync(phone, p_auth)
    cs.sync(desktop, d_auth)

    back = cs.read_custom_data_namespace(desktop, cid, ns)
    assert back is not None and back["src"] == "ai"
    assert json.loads(desktop.get_card(cid).custom_data)[ns]["id"] == "SMD-01"
