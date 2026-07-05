# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""One-click CFA sync setup for the desktop.

Demoing phone<->desktop sync against the self-hosted CFA ``anki-sync-server``
normally means a trip through *Preferences > Syncing* to set a custom URL, then
a separate login. This collapses both into a single action (a CFA-menu item and
a top-bar "Connect" link): point the desktop at the local CFA server, log in
with the fixed CFA credentials, and kick off a normal GUI sync.

It only calls the same PUBLIC ``ProfileManager`` / ``Collection`` sync APIs the
stock GUI uses (``set_custom_sync_url`` / ``sync_login`` / ``set_sync_key`` /
``on_sync_button_clicked``), so it changes no sync/auth behaviour — it just
fills in the fields for you. Credentials/URL match ``tools/cfa/sync_server.py``
and are overridable via the same ``CFA_SYNC_*`` env vars.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aqt.main import AnkiQt

# Match tools/cfa/sync_server.py (and tools/cfa/desktop_sync.py).
CFA_SYNC_URL = os.environ.get("CFA_SYNC_URL", "http://127.0.0.1:27701/")
CFA_SYNC_USER = os.environ.get("CFA_SYNC_USER", "cfa")
CFA_SYNC_PASS = os.environ.get("CFA_SYNC_PASS", "cfa-friday")
CFA_LAST_SYNC_AT_KEY = "cfaLastSyncAt"
_SYNC_STATUS_HOOKS_REGISTERED = False


def account_link_spec(logged_in: bool, account: str | None = None) -> dict[str, str]:
    """The single context-aware sync-account control for the top bar.

    The old top bar showed Sync **and** an always-visible "Connect" **and** an
    always-visible "Log out" — three sync links in a row, with Connect present
    even when already connected and Log out present even when logged out. That
    was the "clunky Connect/Logout" the redesign targets. Now exactly ONE
    account control renders next to Sync, reflecting the actual login state:

    * logged out → ``Connect & Sync`` (link this desktop and start sync), and
    * logged in  → ``Connected`` (names the account and triggers sync).

    Returned as a plain dict so it is unit-testable without Qt; the toolbar
    turns it into a single ``create_link`` and wires the matching handler.
    """
    if logged_in:
        who = account or "your sync account"
        return {
            "cmd": "cfa_connect",
            "label": "Connected",
            "tip": f"Signed in as {who} — click to sync CFA progress",
            "id": "cfa_account",
        }
    return {
        "cmd": "cfa_connect",
        "label": "Connect & Sync",
        "tip": "Connect this desktop to the CFA sync server and start sync",
        "id": "cfa_account",
    }


def register_sync_status_tracking() -> None:
    """Track a lightweight last-sync timestamp for CFA status chrome.

    The stock sync engine does not persist a user-facing "last synced" label on
    desktop, so the CFA Home card records when the existing GUI sync lifecycle
    reports completion. It is presentation-only profile metadata.
    """
    global _SYNC_STATUS_HOOKS_REGISTERED
    if _SYNC_STATUS_HOOKS_REGISTERED:
        return

    import aqt
    from aqt import gui_hooks

    def on_sync_did_finish() -> None:
        try:
            if aqt.mw is not None and aqt.mw.pm.profile is not None:
                aqt.mw.pm.profile[CFA_LAST_SYNC_AT_KEY] = int(time.time())
        except Exception:
            pass

    getattr(gui_hooks, "sync_did_finish").append(on_sync_did_finish)
    _SYNC_STATUS_HOOKS_REGISTERED = True


def connect_cfa_sync(mw: AnkiQt) -> None:
    """Point desktop at the local CFA server, log in, and sync — in one click."""
    from aqt.utils import showWarning, tooltip

    if mw.col is None:
        showWarning("Open a profile first, then Connect.", parent=mw, title="CFA Sync")
        return

    sync_auth = getattr(mw.pm, "sync_auth", lambda: None)
    if sync_auth() is not None:
        account = mw.pm.profile.get("syncUser") or "your sync account"
        tooltip(f"Syncing CFA progress for {account}…", parent=mw)
        mw.on_sync_button_clicked()
        return

    # 1. Point at the local CFA server. set_custom_sync_url also drops any stale
    #    AnkiWeb redirect URL, so the custom endpoint actually takes effect.
    mw.pm.set_custom_sync_url(CFA_SYNC_URL)

    # 2. Log in against that server (mints a fresh hkey). This is the same call
    #    the stock login dialog makes; on localhost it returns in well under a
    #    second, so a direct call is fine.
    try:
        auth = mw.col.sync_login(CFA_SYNC_USER, CFA_SYNC_PASS, CFA_SYNC_URL)
    except Exception as exc:
        showWarning(
            f"Couldn't reach the CFA sync server at {CFA_SYNC_URL}.\n\n"
            "Start it in a terminal with:\n\n    just cfa-syncserver\n\n"
            "…then click Connect again.\n\n"
            f"(details: {exc})",
            parent=mw,
            title="CFA Sync",
        )
        return

    mw.pm.set_sync_key(auth.hkey)
    mw.pm.set_sync_username(CFA_SYNC_USER)

    # Flip the top-bar account control from "Connect & Sync" to "Connected" right away
    # (the single context-aware control keys off pm.sync_auth()).
    try:
        mw.toolbar.draw()
    except Exception:
        pass

    # 3. Run the normal GUI sync — it shows the progress UI and, on the very
    #    first sync of a device, the Download-from / Upload-to direction choice.
    tooltip(
        f"Connected to the CFA sync server as {CFA_SYNC_USER} — syncing…",
        parent=mw,
    )
    mw.on_sync_button_clicked()
