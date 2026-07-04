#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork. Stand up a *long-running* local ``anki-sync-server`` with fixed
credentials, bound to the LAN, so a real desktop ankiCFA and an AnkiDroid
emulator/device can sync against ONE host and round-trip reviews.

This is the manual, interactive companion to ``tools/cfa/sync_roundtrip.py``
(which drives an automated, self-contained round-trip for CI). Here the server
runs in the foreground until Ctrl-C, and prints the exact URLs + credentials
each client should use. See ``docs/cfa/SYNC-SETUP.md``.

Everything is overridable by env var; the defaults are chosen so the whole team
uses the same fixed values:

    CFA_SYNC_USER      (default: cfa)
    CFA_SYNC_PASS      (default: cfa-exam-2026)
    CFA_SYNC_PORT      (default: 27701)
    CFA_SYNC_HOST      (default: 0.0.0.0 — bind all interfaces, LAN-reachable)
    CFA_SYNC_BASE      (default: ~/.cfa-syncserver — PERSISTENT so data survives
                        restarts; the round-trip demo uses a throwaway temp dir)

No password is printed to any network log; it appears only in this local
console so you can type it into the clients.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path


def _lan_ip() -> str:
    """Best-effort primary LAN IPv4 (no traffic is actually sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    user = os.environ.get("CFA_SYNC_USER", "cfa")
    password = os.environ.get("CFA_SYNC_PASS", "cfa-exam-2026")
    port = os.environ.get("CFA_SYNC_PORT", "27701")
    host = os.environ.get("CFA_SYNC_HOST", "0.0.0.0")
    base = os.environ.get(
        "CFA_SYNC_BASE", str(Path.home() / ".cfa-syncserver")
    )
    Path(base).mkdir(parents=True, exist_ok=True)

    # The Rust sync server reads these standard anki-sync-server env vars.
    os.environ["SYNC_HOST"] = host
    os.environ["SYNC_PORT"] = str(port)
    os.environ["SYNC_BASE"] = base
    os.environ["SYNC_USER1"] = f"{user}:{password}"

    lan = _lan_ip()
    bar = "=" * 68
    print(bar)
    print(" ankiCFA sync server — fixed-credential LAN round-trip harness")
    print(bar)
    print(f"  user / pass : {user} / {password}")
    print(f"  data dir    : {base}")
    print(f"  bound to    : {host}:{port}")
    print("  ------------------------------------------------------------------")
    print("  Point each client's custom sync URL at:")
    print(f"    desktop (same machine) : http://127.0.0.1:{port}/")
    print(f"    desktop (another LAN box)/ real phone : http://{lan}:{port}/")
    print(f"    Android emulator       : http://10.0.2.2:{port}/")
    print("  ------------------------------------------------------------------")
    print("  Desktop: Preferences ▸ Syncing ▸ self-hosted sync server URL.")
    print("  AnkiDroid: Settings ▸ Sync ▸ Custom sync server (see SYNC-SETUP.md).")
    print("  Ctrl-C to stop. Data persists across restarts.")
    print(bar, flush=True)

    from anki.syncserver import run_sync_server

    run_sync_server()


if __name__ == "__main__":
    main()
