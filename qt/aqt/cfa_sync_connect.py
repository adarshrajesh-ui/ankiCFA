# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA sync for the desktop — a thin CFA-branded wrapper over *normal Anki sync*.

The CFA product syncs through ordinary Anki collection sync (AnkiWeb by
default, or whatever server the user configures in *Preferences > Syncing*).
There is no custom CFA sync server in the product path: CFA state rides inside
the collection as notes/cards/revlog/config/custom-data and travels with the
normal sync, so "Sync" and "Connect & Sync" simply drive Anki's own sync/login
flow (``on_sync_button_clicked``) — which opens the AnkiWeb login dialog when
the device isn't linked yet and otherwise syncs.

Earlier builds hard-pointed the profile at a *local* dev sync server
(``http://127.0.0.1:27701/``) with fixed credentials. If that loopback URL is
still persisted it makes every sync silently target a server that isn't running
(the "sync is dead" symptom), so :func:`heal_stale_local_sync_url` clears it and
lets Anki fall back to AnkiWeb. The optional self-hosted dev server lives on in
``tools/cfa/sync_server.py`` for testing only, not as the product path.
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aqt.main import AnkiQt

logger = logging.getLogger(__name__)


def _env_or_default(name: str, default: str) -> str:
    return os.environ.get(name) or default


# Defaults for the OPTIONAL developer self-hosted sync server
# (``tools/cfa/sync_server.py`` / ``tools/cfa/desktop_sync.py``). These are NOT
# used by the product sync path — the desktop syncs through normal Anki sync.
CFA_SYNC_URL = _env_or_default("CFA_SYNC_URL", "http://127.0.0.1:27701/")
CFA_SYNC_USER = _env_or_default("CFA_SYNC_USER", "cfa")
CFA_SYNC_PASS = _env_or_default("CFA_SYNC_PASS", "cfa-friday")
CFA_LAST_SYNC_AT_KEY = "cfaLastSyncAt"
# The collection modification time captured at the last completed sync, plus a
# derived flag recording whether the collection actually changed between the two
# most recent syncs. Together they let the Home/sync UI say "Synced as <account>"
# vs "Already up to date" (a no-op sync) without touching Anki's sync internals.
CFA_LAST_SYNC_MOD_KEY = "cfaLastSyncMod"
CFA_LAST_SYNC_CHANGED_KEY = "cfaLastSyncChanged"
SYNC_DIALOG_MIN_WIDTH = 280
SYNC_DIALOG_DEFAULT_WIDTH = 390
SYNC_DIALOG_DEFAULT_HEIGHT = 430
SYNC_DIALOG_BUTTON_MIN_HEIGHT = 44
SYNC_DIALOG_SCREEN_MARGIN = 32


def _sync_dialog_width(mw: AnkiQt | None) -> int:
    """Return a dialog width that fits small screens without desktop source churn."""
    width = SYNC_DIALOG_DEFAULT_WIDTH
    try:
        handle = mw.windowHandle() if mw is not None else None
        screen = handle.screen() if handle is not None else None
        available = screen.availableGeometry().width() if screen is not None else 0
    except Exception:
        available = 0
    if available > 0:
        width = min(
            width, max(SYNC_DIALOG_MIN_WIDTH, available - SYNC_DIALOG_SCREEN_MARGIN)
        )
    return width


def _is_loopback_url(url: str | None) -> bool:
    """True when ``url`` targets a loopback host (a local dev sync server)."""
    if not url:
        return False
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in ("127.0.0.1", "localhost", "::1", "0.0.0.0")


def heal_stale_local_sync_url(mw: AnkiQt | None) -> bool:
    """Drop a stale loopback sync URL so sync uses AnkiWeb / the user's server.

    A loopback URL is never a real product endpoint — it is the leftover local
    dev server that earlier CFA builds configured. It can be persisted in EITHER
    of the two slots ``sync_endpoint()`` consults
    (``currentSyncUrl or customSyncUrl``, see profiles.py): the user-set
    ``customSyncUrl`` OR the ``currentSyncUrl`` the server last redirected us to.
    A stale loopback in *either* slot makes every sync silently target a dead
    ``127.0.0.1`` server (the "sync is dead" symptom), so we clear whichever
    loopback slot is set and let Anki fall back to AnkiWeb (or whatever the user
    configures in Preferences).

    Crucially, a legitimate non-loopback custom/self-host endpoint is left
    untouched. Returns True if a stale URL was cleared. Idempotent (a second
    call is a no-op once healed) and never raises.
    """
    if mw is None:
        return False
    healed = False
    # Slot 1: a stale loopback *custom* server (user- or old-build-configured).
    try:
        custom = mw.pm.custom_sync_url()
    except Exception:
        custom = None
    if _is_loopback_url(custom):
        try:
            mw.pm.set_custom_sync_url(None)
            healed = True
        except Exception:
            logger.warning(
                "Failed clearing stale loopback custom sync URL", exc_info=True
            )
    # Slot 2: a stale loopback *current* endpoint the server last redirected us
    # to. sync_endpoint() prefers this over the custom URL, so a leftover
    # loopback here hijacks sync even after the custom slot is already clean.
    try:
        current = mw.pm._current_sync_url()
    except Exception:
        current = None
    if _is_loopback_url(current):
        try:
            mw.pm.set_current_sync_url(None)
            healed = True
        except Exception:
            logger.warning(
                "Failed clearing stale loopback current sync URL", exc_info=True
            )
    if healed:
        logger.info("Cleared stale loopback CFA sync URL; using AnkiWeb")
    return healed


_SYNC_TRACKING_REGISTERED = False
_ENDPOINT_HEAL_REGISTERED = False


def register_endpoint_healing(mw: AnkiQt) -> None:
    """Heal a stale loopback sync endpoint once on every collection load.

    :func:`heal_stale_local_sync_url` already runs before each *manual* sync
    (trigger/connect), but auto-sync-on-open fires from the profile-load flow
    without going through those wrappers. ``collection_did_load`` runs before
    that auto-sync (see ``AnkiQt.loadProfile``), so healing here guarantees the
    desktop targets AnkiWeb from the moment a profile opens — not just when the
    user clicks Sync. Registration is idempotent and never raises.
    """
    global _ENDPOINT_HEAL_REGISTERED
    if _ENDPOINT_HEAL_REGISTERED:
        return
    _ENDPOINT_HEAL_REGISTERED = True

    from aqt import gui_hooks

    def on_collection_load(_col: Any) -> None:
        heal_stale_local_sync_url(mw)

    gui_hooks.collection_did_load.append(on_collection_load)


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
        "tip": "Connect this device and sync CFA progress",
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
    return (endpoint or "").strip()


def _sync_endpoint_label(endpoint: str | None) -> str:
    """Human label for the sync target, never a raw URL: a configured custom
    server reads as "Custom server"; the default (AnkiWeb) reads as "AnkiWeb"."""
    return "Custom server" if (endpoint or "").strip() else "AnkiWeb"


def sync_connection_error_message(_endpoint: str | None = None) -> str:
    """Product-safe connection error text for the normal dialog surface."""
    return (
        "ankiCFA couldn't connect this device to sync.\n\n"
        "Open Settings & Sync, confirm your account is connected, then try "
        "Connect & Sync again."
    )


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
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sync_result_label(
    *,
    connected: bool,
    syncing: bool,
    account: str | None,
    endpoint_label: str,
    last_synced_at: str | None,
    last_sync_changed: bool | None,
) -> str:
    """A plain, human post-sync result naming the account + endpoint.

    Makes two things the user kept asking about obvious: (1) *which* AnkiWeb
    account this device is synced as (so a two-login mismatch stands out) and
    (2) whether the last sync actually did anything ("Already up to date" for a
    no-op vs "Synced as <account>").
    """
    who = account or "your sync account"
    if syncing:
        return f"Syncing with {endpoint_label} as {who}…"
    if not connected:
        return "Connect this device to sync your CFA progress across devices."
    if not last_synced_at:
        return f"Signed in as {who} ({endpoint_label}). Sync now to update this device."
    if last_sync_changed is False:
        return f"Already up to date as {who} ({endpoint_label})."
    return f"Synced as {who} ({endpoint_label})."


def sync_status_payload(mw: AnkiQt | None) -> dict[str, Any]:
    """Small, UI-only status block shared by Home, toolbar and sync dialog."""
    profile = _profile(mw)
    connected = _is_connected(mw)
    syncing = _is_syncing(mw)
    account = profile.get("syncUser") if connected else None
    last_synced_at = profile.get(CFA_LAST_SYNC_AT_KEY)
    last_sync_changed = profile.get(CFA_LAST_SYNC_CHANGED_KEY)
    endpoint_label = _sync_endpoint_label(_sync_endpoint(mw))
    if syncing:
        status = "Syncing"
        tone = "warn"
        detail = "Sync is running now. You can keep studying while media finishes."
    elif connected:
        status = "Connected"
        tone = "pass"
        detail = "Ready to sync reviews, progress, and settings when you want this device current."
    else:
        status = "Not connected"
        tone = "muted"
        detail = "Connect this device once to keep reviews, progress, and settings current across devices."
    return {
        "connected": connected,
        "syncing": syncing,
        "status": status,
        "tone": tone,
        "account": account or "Not connected",
        "lastSyncedAt": last_synced_at,
        "lastSyncedLabel": _last_synced_label(last_synced_at),
        "endpoint": endpoint_label if connected else "Not connected",
        "detail": detail,
        "resultLabel": _sync_result_label(
            connected=connected,
            syncing=syncing,
            account=account,
            endpoint_label=endpoint_label,
            last_synced_at=last_synced_at,
            last_sync_changed=(
                last_sync_changed if isinstance(last_sync_changed, bool) else None
            ),
        ),
        "actionLabel": "Sync now" if connected else "Connect & Sync",
    }


def _collection_mod(mw: AnkiQt | None) -> int | None:
    """The collection modification timestamp, or None if unavailable.

    Read defensively: this is UI metadata, so a closed/absent collection must
    never raise into the sync-finished hook.
    """
    try:
        col = getattr(mw, "col", None)
        if col is None:
            return None
        mod = col.mod
    except Exception:
        return None
    return int(mod) if isinstance(mod, int) else None


def mark_sync_finished(mw: AnkiQt | None) -> None:
    """Record the sync timestamp and whether this sync actually changed data.

    ``changed`` compares the collection modification time against the value
    captured at the previous sync: equal means nothing moved in either
    direction (a genuine no-op → "Already up to date"), different means reviews,
    ethics attempts, config or internal state were uploaded or downloaded
    (→ "Synced as <account>"). The very first recorded sync counts as a change.
    """
    profile = _profile(mw)
    if not profile:
        return
    current_mod = _collection_mod(mw)
    if current_mod is None:
        # Can't tell (no open collection); don't claim a no-op.
        profile[CFA_LAST_SYNC_CHANGED_KEY] = True
    else:
        previous_mod = profile.get(CFA_LAST_SYNC_MOD_KEY)
        profile[CFA_LAST_SYNC_CHANGED_KEY] = previous_mod != current_mod
        profile[CFA_LAST_SYNC_MOD_KEY] = current_mod
    profile[CFA_LAST_SYNC_AT_KEY] = _now_iso()


# The open CFA product state -> the SvelteKit page to reload after a sync. Every
# CFA screen derives its numbers from the collection (revlog/cards/config), so a
# reload after sync is all that is needed for synced reviews and config to move
# Home, Study, Concept Map and Readiness.
_CFA_STATE_PAGES = {
    "cfaHome": "cfa-home",
    "cfaStudy": "cfa-study",
    "cfaConceptMap": "cfa-concept-map",
    "cfaReadiness": "cfa-readiness/0",
    "cfaProgress": "graphs",
}


def register_sync_status_tracking(mw: AnkiQt) -> None:
    """Persist a last-sync timestamp and refresh the open CFA screen after sync."""
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
        # Refresh whichever CFA screen is open so the just-synced collection
        # (reviews, ethics attempts, exam config, internal state) is reflected
        # immediately instead of on the next manual navigation.
        try:
            page = _CFA_STATE_PAGES.get(getattr(mw, "state", ""))
            if page is not None:
                mw.web.load_sveltekit_page(page)
        except Exception:
            pass

    gui_hooks.sync_did_finish.append(on_sync_finished)


def open_sync_settings(mw: AnkiQt) -> None:
    """Open the native CFA sync status/actions dialog."""
    from aqt.cfa_style import apply
    from aqt.qt import QDialog, QLabel, QPushButton, QVBoxLayout, qconnect

    status = sync_status_payload(mw)
    dialog = QDialog(mw)
    dialog.setObjectName("cfaSyncDialog")
    dialog.setWindowTitle("ankiCFA - Settings & Sync")
    dialog_width = _sync_dialog_width(mw)
    dialog.setMinimumWidth(min(SYNC_DIALOG_MIN_WIDTH, dialog_width))
    dialog.resize(dialog_width, SYNC_DIALOG_DEFAULT_HEIGHT)
    dialog.setSizeGripEnabled(True)
    apply(dialog)
    dialog.setStyleSheet(
        dialog.styleSheet()
        + f"""
        QDialog#cfaSyncDialog QPushButton {{
            min-height: {SYNC_DIALOG_BUTTON_MIN_HEIGHT}px;
            border-radius: 12px;
            padding: 8px 14px;
        }}
        QLabel#cfaSyncHeading {{
            font-size: 22px;
            font-weight: 700;
        }}
        QLabel#cfaSyncRow {{
            padding: 8px 10px;
            border: 1px solid #DDEDEA;
            border-radius: 12px;
            background: #FFFFFF;
        }}
        """
    )

    layout = QVBoxLayout()
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)
    heading = QLabel("Sync your CFA prep")
    heading.setObjectName("cfaSyncHeading")
    heading.setMinimumWidth(0)
    heading.setWordWrap(True)
    layout.addWidget(heading)

    for label, value in (
        ("Status", status["status"]),
        ("Account", status["account"]),
        ("Last synced", status["lastSyncedLabel"]),
    ):
        row = QLabel(f"<b>{label}:</b> {value}")
        row.setObjectName("cfaSyncRow")
        row.setMinimumWidth(0)
        row.setWordWrap(True)
        layout.addWidget(row)

    detail = QLabel(str(status["detail"]))
    detail.setMinimumWidth(0)
    detail.setWordWrap(True)
    layout.addWidget(detail)

    buttons = QVBoxLayout()
    buttons.setSpacing(8)
    primary = QPushButton(str(status["actionLabel"]))
    primary.setDefault(True)
    primary.setMinimumHeight(SYNC_DIALOG_BUTTON_MIN_HEIGHT)

    def run_primary() -> None:
        dialog.accept()
        # connect_cfa_sync heals any stale local URL and drives the normal Anki
        # sync flow, which handles both the linked and not-yet-linked cases.
        connect_cfa_sync(mw)

    qconnect(primary.clicked, run_primary)
    buttons.addWidget(primary)

    if status["connected"]:
        logout = QPushButton("Log out")
        logout.setMinimumHeight(SYNC_DIALOG_BUTTON_MIN_HEIGHT)

        def run_logout() -> None:
            dialog.accept()
            import aqt.cfa

            aqt.cfa.logout_of_sync(mw)

        qconnect(logout.clicked, run_logout)
        buttons.addWidget(logout)

    close = QPushButton("Close")
    close.setMinimumHeight(SYNC_DIALOG_BUTTON_MIN_HEIGHT)
    qconnect(close.clicked, dialog.reject)
    buttons.addWidget(close)
    layout.addLayout(buttons)
    dialog.setLayout(layout)
    dialog.exec()


def trigger_cfa_sync(mw: AnkiQt) -> None:
    """Toolbar/page Sync entry point — always the normal Anki sync flow.

    ``on_sync_button_clicked`` opens the AnkiWeb login dialog when the device is
    not linked yet and otherwise syncs, so a single call covers both states. Any
    stale loopback dev URL is dropped first so sync targets AnkiWeb, not a dead
    local server.
    """
    if not hasattr(mw, "col"):
        if getattr(mw.pm, "sync_auth", lambda: None)() is None:
            open_sync_settings(mw)
        else:
            mw.on_sync_button_clicked()
        return
    if mw.col is None:
        open_sync_settings(mw)
        return
    heal_stale_local_sync_url(mw)
    mw.on_sync_button_clicked()


def connect_cfa_sync(mw: AnkiQt) -> None:
    """Sync this desktop using normal Anki sync (AnkiWeb by default).

    No custom server and no fixed credentials: drop any stale loopback dev URL,
    then run Anki's own sync flow, which opens the AnkiWeb login when the device
    isn't linked yet and otherwise syncs. CFA state travels inside the collection
    (notes/cards/revlog/config/custom-data), so the normal sync carries it all.
    """
    from aqt.utils import showWarning

    if mw.col is None:
        showWarning(
            "Open a profile first, then sync your CFA progress.",
            parent=mw,
            title="ankiCFA — Sync",
        )
        return

    heal_stale_local_sync_url(mw)
    mw.on_sync_button_clicked()
