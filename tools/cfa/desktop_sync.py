#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA desktop-side sync driver (Feature 9 — real two-way sync).

Points a *real* desktop Anki ``Collection`` at the self-hosted CFA
``anki-sync-server`` and logs in / syncs with the fixed CFA credentials —
mirroring what desktop Anki's *Preferences > Syncing > Self-hosted sync server*
does (a custom sync URL plus a username/password login that mints an hkey).

It is the "desktop device" in the phone<->desktop round-trip proofs: the phone
(AnkiDroid on the emulator) and this script both talk to the *same* server, so a
review made on one shows up on the other after a sync.

Desktop custom-sync-URL config, the GUI equivalent of what this does:
    Preferences > Syncing > Self-hosted sync server = http://127.0.0.1:27701/
    then log in as  cfa / cfa-friday.
Here we drive the same Rust sync engine headlessly via ``Collection.sync_login``
/ ``Collection.sync_collection`` (through ``anki.cfa_sync``), so no GUI needed.

Sub-commands
------------
sync     open the desktop collection, log in, sync (full up/down as required),
         print a summary of decks / cards / notes / revlog rows.
status   open and print the summary without syncing.
review   review N due cards in a deck at a given ease (does NOT sync).
dump     print the revlog rows for a card id (or all), newest last.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MAIN = os.environ.get("CFA_MAIN_TREE", "/Users/adarshrajesh/AlphaWeek2/ankiCFA")
# Insert compiled/generated first, worktree source LAST so it lands at sys.path[0]
# and our edited pylib/anki/*.py win the namespace-package merge (the .so and
# generated modules resolve from the main tree's out/pylib).
for _p in (
    os.path.join(_REPO, "out", "pylib"),
    os.path.join(_MAIN, "out", "pylib"),
    os.path.join(_REPO, "pylib"),
):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from anki import cfa_sync as cs  # noqa: E402
from anki.collection import Collection  # noqa: E402

# Fixed CFA sync facts (match tools/cfa/sync_server.py).
CFA_HOST = os.environ.get("CFA_SYNC_HOST", "127.0.0.1")
CFA_PORT = int(os.environ.get("CFA_SYNC_PORT", "27701"))
CFA_USER = os.environ.get("CFA_SYNC_USER", "cfa")
CFA_PASS = os.environ.get("CFA_SYNC_PASS", "cfa-friday")
CFA_ENDPOINT = os.environ.get("CFA_SYNC_URL", f"http://{CFA_HOST}:{CFA_PORT}/")
CFA_DESKTOP_BASE = os.environ.get("CFA_DESKTOP_BASE", "/tmp/cfa-desktop")


def open_col(base: str) -> Collection:
    os.makedirs(base, exist_ok=True)
    return Collection(os.path.join(base, "collection.anki2"))


def summarize(col: Collection) -> dict:
    decks = {d.name: d.id for d in col.decks.all_names_and_ids()}
    return {
        "cards": col.card_count(),
        "notes": col.note_count(),
        "revlog": col.db.scalar("select count() from revlog") or 0,
        "decks": sorted(decks),
    }


def cmd_sync(args: argparse.Namespace) -> int:
    col = open_col(args.base)
    try:
        auth = cs.login(col, _server_stub())  # type: ignore[arg-type]
        before = summarize(col)
        required = cs.sync(col, auth)
        after = summarize(col)
        result = {
            "endpoint": CFA_ENDPOINT,
            "username": CFA_USER,
            "sync_result": _required_name(required),
            "before": before,
            "after": after,
        }
        print("CFA_DESKTOP_SYNC " + json.dumps(result, indent=2))
        return 0
    finally:
        col.close()


def cmd_status(args: argparse.Namespace) -> int:
    col = open_col(args.base)
    try:
        print(json.dumps({"endpoint": CFA_ENDPOINT, **summarize(col)}, indent=2))
        return 0
    finally:
        col.close()


def cmd_review(args: argparse.Namespace) -> int:
    col = open_col(args.base)
    try:
        if args.deck:
            did = col.decks.id_for_name(args.deck)
            if did is None:
                print(f"no such deck: {args.deck}", file=sys.stderr)
                return 2
            col.decks.select(did)
        reviewed = []
        for _ in range(args.count):
            card = col.sched.getCard()
            if card is None:
                break
            card.start_timer()
            col.sched.answerCard(card, args.ease)
            reviewed.append(card.id)
        print(json.dumps({"reviewed": reviewed, "ease": args.ease}, indent=2))
        return 0
    finally:
        col.close()


def cmd_dump(args: argparse.Namespace) -> int:
    col = open_col(args.base)
    try:
        if args.card:
            rows = col.db.all(
                "select id, cid, ease, type from revlog where cid=? order by id",
                args.card,
            )
        else:
            rows = col.db.all(
                "select id, cid, ease, type from revlog order by id",
            )
        out = [
            {"id": int(r[0]), "cid": int(r[1]), "ease": int(r[2]), "type": int(r[3])}
            for r in rows
        ]
        print(json.dumps({"count": len(out), "revlog": out}, indent=2))
        return 0
    finally:
        col.close()


class _ServerStub:
    """Minimal stand-in for cfa_sync.SyncServerHandle (login only needs creds)."""

    username = CFA_USER
    password = CFA_PASS
    endpoint = CFA_ENDPOINT


def _server_stub() -> _ServerStub:
    return _ServerStub()


def _required_name(required: int) -> str:
    for name in (
        "NO_CHANGES",
        "NORMAL_SYNC",
        "FULL_SYNC",
        "FULL_DOWNLOAD",
        "FULL_UPLOAD",
    ):
        if getattr(cs, name, object()) == required:
            return name
    return str(required)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=CFA_DESKTOP_BASE, help="desktop collection dir")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sync").set_defaults(func=cmd_sync)
    sub.add_parser("status").set_defaults(func=cmd_status)

    p_rev = sub.add_parser("review")
    p_rev.add_argument("--deck", default=None)
    p_rev.add_argument("--count", type=int, default=1)
    p_rev.add_argument("--ease", type=int, default=3)
    p_rev.set_defaults(func=cmd_review)

    p_dump = sub.add_parser("dump")
    p_dump.add_argument("--card", type=int, default=None)
    p_dump.set_defaults(func=cmd_dump)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
