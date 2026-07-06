#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Feature F8 — narrated cross-platform persistence proof.

Stands up a real local ``anki-sync-server`` (the same Rust sync engine that
runs on-device under AnkiDroid per F6), seeds a desktop collection with the CFA
study deck + the ethics minimal-pairs deck + the fork exam config, syncs, and
then prints exactly what shows up on a FRESH "phone" collection after a full
download — including the shared-engine exam queue built against the synced
content. Nothing is faked: the phone side is a genuine Rust-backed Collection
downloaded through the sync protocol.

Run via ``just cfa-sync`` peers; invoke directly:

    PYTHONPATH=out/pylib:pylib:. out/pyenv/bin/python tools/cfa/f8_persistence_proof.py
"""

# pylint: disable=import-error

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "cfa", "ethics_pairs"))

import import_pairs as P  # noqa: E402

from anki import cfa  # noqa: E402
from anki import cfa_sync as cs
from anki.collection import Collection  # noqa: E402

CFA_DECK = "CFA Level II"
ETHICS_DECK = P.nt.DECK_NAME
ETHICS_NOTETYPE = P.nt.NOTETYPE_NAME
EXAM_DATE = "2026-08-25"
TOPIC_WEIGHTS = {"los::ethics": 0.20, "los::equity": 0.15, "los::fixed-income": 0.15}


def _new_col(base: str, name: str) -> Collection:
    path = os.path.join(base, f"{name}.anki2")
    return Collection(path)


def _seed_desktop(col: Collection) -> None:
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
        note = col.new_note(col.models.by_name("Basic"))
        note["Front"] = front
        note["Back"] = back
        note.tags = tags
        col.add_note(note, deck_id)
    P.import_pairs(col, P.load_pairs()[:5])
    cfa.set_exam_config(col, exam_date=EXAM_DATE, topic_weights=TOPIC_WEIGHTS)


def main() -> int:
    base = tempfile.mkdtemp(prefix="gnhf-cfa-f8-proof-")
    srv_base = os.path.join(base, "server")
    os.makedirs(srv_base, exist_ok=True)

    print("=" * 70)
    print("F8 CROSS-PLATFORM PERSISTENCE — desktop -> sync -> fresh phone")
    print("=" * 70)

    with cs.sync_server(srv_base) as server:
        print(f"\n[1] Local anki-sync-server up at {server.endpoint}")
        print("    (identical Rust sync engine to the on-device fork, per F6)")

        desktop = _new_col(base, "desktop")
        _seed_desktop(desktop)
        print("\n[2] Seeded DESKTOP collection:")
        print(
            f"      decks       : {sorted(d.name for d in desktop.decks.all_names_and_ids())}"
        )
        print(f"      notes       : {desktop.note_count()}")
        print(f"      exam config : {cfa.get_exam_config(desktop)}")

        d_auth = cs.login(desktop, server)
        cs.sync(desktop, d_auth)
        print("\n[3] Desktop synced -> server seeded (full upload)")

        phone = _new_col(base, "phone")
        print("\n[4] Fresh empty PHONE collection created:")
        print(f"      notes before sync : {phone.note_count()}")
        p_auth = cs.login(phone, server)
        cs.sync(phone, p_auth)
        print("      ...full download...")

        print("\n[5] PHONE collection AFTER sync:")
        deck_names = sorted(d.name for d in phone.decks.all_names_and_ids())
        print(f"      decks              : {deck_names}")
        print(f"      notes              : {phone.note_count()}")
        notetypes = sorted(nt["name"] for nt in phone.models.all())
        print(f"      note-types         : {notetypes}")
        ethics_nids = phone.find_notes(f'note:"{ETHICS_NOTETYPE}"')
        print(f"      ethics cards       : {len(ethics_nids)}")
        cfg = cfa.get_exam_config(phone)
        print(f"      exam config        : {cfg}")
        dte = cfa.days_to_exam(phone, today=date(2026, 7, 3))
        print(f"      days_to_exam(7/3)  : {dte}")

        print("\n[6] SHARED-ENGINE exam queue (Rust BuildExamQueue) on the phone:")
        deck_id = phone.decks.id(CFA_DECK)
        queue = cfa.build_exam_queue(phone, deck_id=deck_id)
        print(f"      card_ids (weakest-first): {list(queue.card_ids)}")
        print(f"      scores                  : {[round(s, 4) for s in queue.scores]}")

        # honest checks
        ok = (
            CFA_DECK in deck_names
            and ETHICS_DECK in deck_names
            and cfg == {"exam_date": EXAM_DATE, "topic_weights": TOPIC_WEIGHTS}
            and len(ethics_nids) == 5
            and len(queue.card_ids) == 3
        )
        desktop.close()
        phone.close()
        print("\n" + "=" * 70)
        print(
            "RESULT:",
            "PASS — all CFA content + exam config + shared-engine queue reached the phone"
            if ok
            else "FAIL",
        )
        print("=" * 70)
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
