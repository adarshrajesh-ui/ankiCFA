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
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aqt.main import AnkiQt

# Match tools/cfa/sync_server.py (and tools/cfa/desktop_sync.py).
CFA_SYNC_URL = os.environ.get("CFA_SYNC_URL", "http://127.0.0.1:27701/")
CFA_SYNC_USER = os.environ.get("CFA_SYNC_USER", "cfa")
CFA_SYNC_PASS = os.environ.get("CFA_SYNC_PASS", "cfa-friday")
CFA_LAST_SYNC_AT_KEY = "cfaLastSyncAt"

_SYNC_TRACKING_REGISTERED = False


def account_link_spec(logged_in: bool, account: str | None = None) -> dict[str, str]:
    """The single context-aware sync-account control for the top bar.

    The old top bar showed Sync **and** an always-visible "Connect" **and** an
    always-visible "Log out" — three sync links in a row, with Connect present
    even when already connected and Log out present even when logged out. That
    was the "clunky Connect/Logout" the redesign targets. Now exactly ONE
    account control renders next to Sync, reflecting the actual login state:

    * logged out → ``Connect & Sync`` (invites you to link this desktop), and
    * logged in  → ``Sync settings`` (names the account in its tooltip).

    Returned as a plain dict so it is unit-testable without Qt; the toolbar
    turns it into a single ``create_link`` and wires the matching handler.
    """
    if logged_in:
        who = account or "your sync account"
        return {
            "cmd": "cfa_sync_settings",
            "label": "Sync settings",
            "tip": f"Signed in as {who} — open sync status and account settings",
            "id": "cfa_account",
        }
    return {
        "cmd": "cfa_sync_settings",
        "label": "Connect & Sync",
        "tip": "Connect this desktop to the CFA sync server and sync",
        "id": "cfa_account",
    }


def _profile(mw: AnkiQt | None) -> dict[str, Any]:
    try:
        profile = getattr(getattr(mw, "pm", None), "profile", None)
    except Exception:
        return {}
    return profile if isinstance(profile, dict) else {}


def _is_connected(mw: AnkiQt | None) -> bool:
    try:
        return bool(mw and mw.pm.sync_auth() is not None)
    except Exception:
        return False


def _is_syncing(mw: AnkiQt | None) -> bool:
    try:
        return bool(mw and mw.media_syncer.is_syncing())
    except Exception:
        return False


def _sync_endpoint(mw: AnkiQt | None) -> str:
    try:
        endpoint = mw.pm.sync_endpoint() if mw is not None else None
    except Exception:
        endpoint = None
    return endpoint or CFA_SYNC_URL


def _last_synced_label(value: str | None) -> str:
    if not value:
        return "Not synced yet"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        local = parsed.astimezone()
        hour = local.strftime("%I").lstrip("0") or "0"
        return f"{local:%b} {local.day}, {local.year} at {hour}:{local:%M %p}"
    except Exception:
        return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sync_status_payload(mw: AnkiQt | None) -> dict[str, Any]:
    """Small, UI-only status block shared by Home, toolbar and sync dialog."""
    profile = _profile(mw)
    connected = _is_connected(mw)
    syncing = _is_syncing(mw)
    account = profile.get("syncUser") if connected else None
    last_synced_at = profile.get(CFA_LAST_SYNC_AT_KEY)
    if syncing:
        status = "Syncing"
        tone = "warn"
        detail = "Sync is running now. You can keep studying while media finishes."
    elif connected:
        status = "Connected"
        tone = "pass"
        detail = "Offline-ready. Tap Sync now when you want this device current."
    else:
        status = "Not connected"
        tone = "muted"
        detail = "Connect once, then use Sync now from this CFA screen."
    return {
        "connected": connected,
        "syncing": syncing,
        "status": status,
        "tone": tone,
        "account": account or "Not connected",
        "lastSyncedAt": last_synced_at,
        "lastSyncedLabel": _last_synced_label(last_synced_at),
        "endpoint": _sync_endpoint(mw),
        "detail": detail,
        "actionLabel": "Sync now" if connected else "Connect & Sync",
    }


def mark_sync_finished(mw: AnkiQt | None) -> None:
    profile = _profile(mw)
    if profile:
        profile[CFA_LAST_SYNC_AT_KEY] = _now_iso()


def register_sync_status_tracking(mw: AnkiQt) -> None:
    """Persist a lightweight last-sync timestamp for CFA status surfaces."""
    global _SYNC_TRACKING_REGISTERED
    if _SYNC_TRACKING_REGISTERED:
        return
    _SYNC_TRACKING_REGISTERED = True

    from aqt import gui_hooks

    def on_sync_finished() -> None:
        mark_sync_finished(mw)
        try:
            mw.toolbar.draw()
        except Exception:
            pass
        try:
            if getattr(mw, "state", "") == "cfaHome":
                mw.web.load_sveltekit_page("cfa-home")
        except Exception:
            pass

    gui_hooks.sync_did_finish.append(on_sync_finished)


def open_sync_settings(mw: AnkiQt) -> None:
    """Open the native CFA sync status/actions dialog."""
    from aqt.qt import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, qconnect
    from aqt.cfa_style import apply

    status = sync_status_payload(mw)
    dialog = QDialog(mw)
    dialog.setWindowTitle("ankiCFA — Settings & Sync")
    dialog.resize(430, 260)
    apply(dialog)

    layout = QVBoxLayout()
    heading = QLabel("Settings & Sync")
    heading.setObjectName("cfaSyncHeading")
    layout.addWidget(heading)

    for label, value in (
        ("Status", status["status"]),
        ("Account", status["account"]),
        ("Last synced", status["lastSyncedLabel"]),
        ("Server", status["endpoint"]),
    ):
        row = QLabel(f"<b>{label}:</b> {value}")
        row.setWordWrap(True)
        layout.addWidget(row)

    detail = QLabel(str(status["detail"]))
    detail.setWordWrap(True)
    layout.addWidget(detail)

    buttons = QHBoxLayout()
    primary = QPushButton(str(status["actionLabel"]))
    primary.setDefault(True)

    def run_primary() -> None:
        dialog.accept()
        if sync_status_payload(mw)["connected"]:
            mw.on_sync_button_clicked()
        else:
            connect_cfa_sync(mw)

    qconnect(primary.clicked, run_primary)
    buttons.addWidget(primary)

    if status["connected"]:
        logout = QPushButton("Log out")

        def run_logout() -> None:
            dialog.accept()
            import aqt.cfa

            aqt.cfa.logout_of_sync(mw)

        qconnect(logout.clicked, run_logout)
        buttons.addWidget(logout)

    close = QPushButton("Close")
    qconnect(close.clicked, dialog.reject)
    buttons.addWidget(close)
    layout.addLayout(buttons)
    dialog.setLayout(layout)
    dialog.exec()


def connect_cfa_sync(mw: AnkiQt) -> None:
    """Point desktop at the local CFA server, log in, and sync — in one click."""
    from aqt.utils import showWarning, tooltip

    if mw.col is None:
        showWarning("Open a profile first, then Connect.", parent=mw, title="CFA Sync")
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

    # Flip the top-bar account control from "Connect" to "Log out" right away
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
