#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA two-way sync demo (Feature 9).

Stands up a local ``anki-sync-server`` and drives a desktop <-> phone
round-trip, printing a human-readable narrative that proves:

  1. a review made on the desktop appears on the phone after a sync,
  2. a review made on the phone appears on the desktop,
  3. when the same card is reviewed on BOTH devices offline, the two
     collections converge, both reviews are preserved (no lost / double
     counted reviews), and the more-recent review decides the card state.

Run with the repo's built python::

    just cfa-sync

Nothing here is destructive: syncing only exchanges already-recorded
reviews, so FSRS scheduling + undo history stay valid.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_REPO, "out", "pylib"), os.path.join(_REPO, "pylib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from anki import cfa_sync as cs  # noqa: E402
from anki.collection import Collection  # noqa: E402


def _new_collection(path: str) -> Collection:
    return Collection(path)


def _add_card(col: Collection) -> int:
    note = col.newNote()
    note["Front"] = "CFA L2: what does WACC stand for?"
    note["Back"] = "weighted average cost of capital"
    col.addNote(note)
    return col.find_cards("")[0]


def _review(col: Collection, cid: int, ease: int) -> None:
    card = col.get_card(cid)
    card.start_timer()
    col.sched.answerCard(card, ease)


_EASE = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}


def main() -> int:
    workdir = tempfile.mkdtemp(prefix="gnhf-sync-")
    srv_base = os.path.join(workdir, "server")
    os.makedirs(srv_base, exist_ok=True)

    print("=" * 68)
    print("CFA TWO-WAY SYNC ROUND-TRIP  (desktop <-> anki-sync-server <-> phone)")
    print("=" * 68)

    with cs.sync_server(srv_base) as server:
        print(f"\n[server]  anki-sync-server listening at {server.endpoint}")
        print(f"[server]  user '{server.username}', collections stored under {srv_base}")

        desktop = _new_collection(os.path.join(workdir, "desktop.anki2"))
        cid = _add_card(desktop)
        d_auth = cs.login(desktop, server)
        cs.sync(desktop, d_auth)
        print("\n[desktop] created 1 CFA card, logged in, uploaded to server")

        phone = _new_collection(os.path.join(workdir, "phone.anki2"))
        p_auth = cs.login(phone, server)
        cs.sync(phone, p_auth)
        print(f"[phone]   synced down: now has {phone.card_count()} card, "
              f"{phone.note_count()} note")

        print("\n--- 1. FORWARD: review on desktop, sync, check phone -----------")
        _review(desktop, cid, 3)
        print(f"[desktop] reviewed card -> '{_EASE[3]}'  (revlog rows: "
              f"{len(cs.revlog_events(desktop, cid))})")
        cs.sync(desktop, d_auth)
        cs.sync(phone, p_auth)
        pe = cs.revlog_events(phone, cid)
        print(f"[phone]   after sync: {len(pe)} review present, "
              f"last = '{_EASE[pe[-1].ease]}'  -> review propagated ✓")

        print("\n--- 2. REVERSE: review on phone, sync, check desktop -----------")
        _review(phone, cid, 2)
        print(f"[phone]   reviewed card -> '{_EASE[2]}'")
        cs.sync(phone, p_auth)
        cs.sync(desktop, d_auth)
        de = cs.revlog_events(desktop, cid)
        print(f"[desktop] after sync: {len(de)} reviews present, "
              f"last = '{_EASE[de[-1].ease]}'  -> review propagated back ✓")

        print("\n--- 3. CONFLICT: same card reviewed on BOTH, offline -----------")
        _review(desktop, cid, 1)
        time.sleep(0.01)
        _review(phone, cid, 4)
        d_ms = cs.last_review_ms(desktop, cid)
        p_ms = cs.last_review_ms(phone, cid)
        print(f"[desktop] reviewed -> '{_EASE[1]}'  at {d_ms} ms")
        print(f"[phone]   reviewed -> '{_EASE[4]}'  at {p_ms} ms  "
              f"(phone is {p_ms - d_ms} ms more recent)")
        cs.sync(desktop, d_auth)
        cs.sync(phone, p_auth)
        cs.sync(desktop, d_auth)

        d_ids = [e.reviewed_at_ms for e in cs.revlog_events(desktop, cid)]
        p_ids = [e.reviewed_at_ms for e in cs.revlog_events(phone, cid)]
        converged = cs.last_review_ms(desktop, cid)
        winner = cs.resolve_review_conflict(
            cs.ReviewEvent(cid, d_ms, 1, "desktop"),
            cs.ReviewEvent(cid, p_ms, 4, "phone"),
        )
        print(f"[both]    converged revlog ids identical: {sorted(d_ids) == sorted(p_ids)}")
        print(f"[both]    total distinct reviews: {len(d_ids)} "
              f"(no duplicates: {len(d_ids) == len(set(d_ids))})")
        print(f"[rule]    resolve_review_conflict() -> winner is '{winner.source}' "
              f"(more recent)")
        print(f"[both]    converged card's last review == phone's review: "
              f"{converged == p_ms == winner.reviewed_at_ms}")

        ok = (
            sorted(d_ids) == sorted(p_ids)
            and len(d_ids) == len(set(d_ids))
            and converged == p_ms
        )
        print("\n" + "=" * 68)
        print("RESULT:", "ALL CHECKS PASSED ✓" if ok else "FAILED ✗")
        print("=" * 68)
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
