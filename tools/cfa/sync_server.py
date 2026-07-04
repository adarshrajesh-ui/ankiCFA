#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA self-hosted sync server launcher (Feature 9 — real two-way sync).

A thin, fixed-credential launcher on top of ``anki.cfa_sync.sync_server`` so
that BOTH the desktop Anki and the AnkiDroid emulator can point at the *same*
locally-hosted ``anki-sync-server`` and log in with identical creds.

Fixed facts (so desktop + phone agree without any hand-off):

    user  = cfa
    pass  = cfa-friday
    port  = 27701
    base  = /tmp/cfa-syncserver           (server-side collection storage)
    host  = 0.0.0.0                        (so the emulator reaches it)

    From the host machine:  http://127.0.0.1:27701/
    From the emulator:      http://10.0.2.2:27701/   (10.0.2.2 == host loopback)

Sub-commands
------------
serve   Run the server in the foreground until Ctrl-C. Prints the endpoint,
        the emulator endpoint, and a freshly-minted ``hkey`` login token (the
        same token AnkiDroid stores after a successful login), so the phone can
        be pointed at the server with a single ``adb`` shared-prefs write.
hkey    Start the server briefly, log in once, print ONLY the hkey, exit.
        (Used by configure_phone_sync.sh to inject a real login token.)

Nothing here is destructive: the server only exchanges already-recorded
reviews, so FSRS scheduling + undo history stay valid.
"""

from __future__ import annotations

import argparse
import json
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

# ---- Fixed CFA sync facts -------------------------------------------------
CFA_SYNC_USER = "cfa"
CFA_SYNC_PASS = "cfa-friday"
CFA_SYNC_PORT = 27701
CFA_SYNC_HOST = "0.0.0.0"
# A fixed, predictable base so desktop, phone-config scripts and tests agree.
CFA_SYNC_BASE = "/tmp/cfa-syncserver"
EMULATOR_HOST = "10.0.2.2"  # Android emulator alias for the host loopback


def _endpoints(port: int) -> tuple[str, str]:
    host_ep = f"http://127.0.0.1:{port}/"
    phone_ep = f"http://{EMULATOR_HOST}:{port}/"
    return host_ep, phone_ep


def _mint_hkey(server) -> str:
    """Log in against the running server and return the real hkey token."""
    tmp = tempfile.mkdtemp(prefix="cfa-hkey-")
    col = Collection(os.path.join(tmp, "hkey.anki2"))
    try:
        auth = cs.login(col, server)
        return auth.hkey
    finally:
        col.close()


def cmd_serve(args: argparse.Namespace) -> int:
    os.makedirs(args.base, exist_ok=True)
    host_ep, phone_ep = _endpoints(args.port)
    with cs.sync_server(
        args.base,
        username=args.user,
        password=args.password,
        host=args.host,
        port=args.port,
    ) as server:
        hkey = _mint_hkey(server)
        info = {
            "user": server.username,
            "password": server.password,
            "port": server.port,
            "host": server.host,
            "base": args.base,
            "host_endpoint": host_ep,
            "phone_endpoint": phone_ep,
            "hkey": hkey,
        }
        # A machine-readable line other scripts can grep for, plus the file.
        with open(args.info_file, "w") as fh:
            json.dump(info, fh, indent=2)
        print("=" * 68)
        print("CFA self-hosted anki-sync-server is UP")
        print("=" * 68)
        print(f"  user / pass     : {server.username} / {server.password}")
        print(f"  host endpoint   : {host_ep}")
        print(f"  phone endpoint  : {phone_ep}   (set this in AnkiDroid)")
        print(f"  collection base : {args.base}")
        print(f"  login hkey      : {hkey}")
        print(f"  info written to : {args.info_file}")
        print("=" * 68)
        print("CFA_SYNC_READY " + json.dumps(info))
        sys.stdout.flush()
        if args.duration:
            time.sleep(args.duration)
            return 0
        try:
            while server.is_up():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[server] shutting down")
        return 0


def cmd_hkey(args: argparse.Namespace) -> int:
    os.makedirs(args.base, exist_ok=True)
    with cs.sync_server(
        args.base,
        username=args.user,
        password=args.password,
        host=args.host,
        port=args.port,
    ) as server:
        print(_mint_hkey(server))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", default=CFA_SYNC_USER)
    ap.add_argument("--password", default=CFA_SYNC_PASS)
    ap.add_argument("--port", type=int, default=CFA_SYNC_PORT)
    ap.add_argument("--host", default=CFA_SYNC_HOST)
    ap.add_argument("--base", default=CFA_SYNC_BASE)
    ap.add_argument(
        "--info-file",
        default=os.path.join(CFA_SYNC_BASE, "server-info.json"),
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="run the server until Ctrl-C")
    p_serve.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="seconds to stay up then exit (0 = forever)",
    )
    p_serve.set_defaults(func=cmd_serve)

    p_hkey = sub.add_parser("hkey", help="print a real login hkey and exit")
    p_hkey.set_defaults(func=cmd_hkey)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
