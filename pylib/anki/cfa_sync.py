# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA two-way sync helpers (Feature 9).

Utilities to stand up a local ``anki-sync-server`` and drive a
desktop <-> phone collection round-trip, plus the documented
review-conflict rule (**more-recent review wins**) that guarantees no
lost or double-counted reviews.

The heavy lifting (the actual sync protocol) is done by Anki's own Rust
sync engine, reached through ``Collection.sync_collection`` /
``Collection.full_upload_or_download``. This module is a thin,
test-friendly driver on top of it so the CFA study flow can prove that a
review made on one device shows up on another and back again.

Nothing here mutates the collection destructively: syncing only exchanges
already-recorded reviews, so FSRS scheduling state and undo history stay
valid.
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Iterator

from anki import sync_pb2
from anki.collection import Collection
from anki.sync import SyncAuth

# The five sync outcomes the backend can report. ``sync_collection`` performs
# a normal sync itself and returns NO_CHANGES / NORMAL_SYNC; for the full
# variants the caller must follow up with ``full_upload_or_download``.
_Required = sync_pb2.SyncCollectionResponse.ChangesRequired
NO_CHANGES = _Required.NO_CHANGES
NORMAL_SYNC = _Required.NORMAL_SYNC
FULL_SYNC = _Required.FULL_SYNC
FULL_DOWNLOAD = _Required.FULL_DOWNLOAD
FULL_UPLOAD = _Required.FULL_UPLOAD


# --------------------------------------------------------------------------
# Standing up the sync server
# --------------------------------------------------------------------------


def _free_port() -> int:
    """Grab a free TCP port. Small race window, fine for local tests."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@dataclass
class SyncServerHandle:
    """A running local sync server plus the credentials to reach it."""

    endpoint: str
    username: str
    password: str
    host: str
    port: int
    process: subprocess.Popen

    def is_up(self) -> bool:
        with contextlib.suppress(OSError):
            with socket.create_connection((self.host, self.port), timeout=0.5):
                return True
        return False


@contextlib.contextmanager
def sync_server(
    base_folder: str,
    *,
    username: str = "user",
    password: str = "pass",
    host: str = "127.0.0.1",
    port: int | None = None,
    startup_timeout: float = 30.0,
) -> Iterator[SyncServerHandle]:
    """Run ``anki-sync-server`` in a subprocess for the duration of the block.

    A subprocess (rather than a thread) is used because the Rust server owns a
    tokio runtime and installs a ctrl-c shutdown handler; a subprocess keeps
    that isolated from the test's own event loop and is torn down cleanly.
    """
    port = port or _free_port()
    env = dict(os.environ)
    env["SYNC_HOST"] = host
    env["SYNC_PORT"] = str(port)
    env["SYNC_BASE"] = base_folder
    env["SYNC_USER1"] = f"{username}:{password}"
    # keep the child importing the same anki we're running
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in [*sys.path, env.get("PYTHONPATH", "")] if p
    )

    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from anki.syncserver import run_sync_server; run_sync_server()",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    handle = SyncServerHandle(
        endpoint=f"http://{host}:{port}/",
        username=username,
        password=password,
        host=host,
        port=port,
        process=proc,
    )
    try:
        deadline = time.time() + startup_timeout
        while time.time() < deadline:
            if proc.poll() is not None:
                out = proc.stdout.read().decode() if proc.stdout else ""
                raise RuntimeError(f"sync server exited early:\n{out}")
            if handle.is_up():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("sync server did not come up in time")
        yield handle
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)
        if proc.poll() is None:
            proc.kill()


# --------------------------------------------------------------------------
# Driving a collection through a sync
# --------------------------------------------------------------------------


def login(col: Collection, server: SyncServerHandle) -> SyncAuth:
    """Authenticate ``col`` against ``server`` and return a SyncAuth."""
    return col.sync_login(server.username, server.password, server.endpoint)


def _full_transfer(
    col: Collection, auth: SyncAuth, *, upload: bool, server_usn: int | None
) -> None:
    col.close_for_full_sync()
    try:
        col.full_upload_or_download(auth=auth, server_usn=server_usn, upload=upload)
    finally:
        col.reopen(after_full_sync=True)


def sync(col: Collection, auth: SyncAuth) -> int:
    """Perform one full sync cycle, resolving whatever the backend requires.

    Returns the ``ChangesRequired`` value the backend reported. For the full
    variants the follow-up transfer is performed automatically.
    """
    out = col.sync_collection(auth, sync_media=False)
    required = out.required
    if required == FULL_DOWNLOAD:
        _full_transfer(col, auth, upload=False, server_usn=out.server_media_usn)
    elif required == FULL_UPLOAD:
        _full_transfer(col, auth, upload=True, server_usn=out.server_media_usn)
    return required


def force_full_upload(col: Collection, auth: SyncAuth) -> None:
    """Seed the server from ``col`` (used for the very first sync)."""
    _full_transfer(col, auth, upload=True, server_usn=None)


def force_full_download(col: Collection, auth: SyncAuth) -> None:
    """Replace ``col`` with the server's copy."""
    _full_transfer(col, auth, upload=False, server_usn=None)


# --------------------------------------------------------------------------
# The conflict rule: more-recent review wins
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewEvent:
    """A single review of a card, as recorded in the revlog.

    ``reviewed_at_ms`` is the revlog id (a millisecond epoch timestamp), which
    Anki guarantees to be unique per row — two reviews of the same card are
    stored as two distinct rows, so no review is ever silently merged away.
    """

    card_id: int
    reviewed_at_ms: int
    ease: int
    source: str = ""


def resolve_review_conflict(a: ReviewEvent, b: ReviewEvent) -> ReviewEvent:
    """Return the winning review when the same card was reviewed on two devices.

    Rule: **the more recent review wins** — the card's final scheduling state
    reflects whichever review happened later in wall-clock time. This mirrors
    Anki's own last-writer-wins merge (higher modification time is kept) and is
    the rule the CFA two-way sync relies on.

    Both reviews still persist in the revlog (they are distinct rows keyed by
    their millisecond ids); only the *current card state* is decided here, so
    nothing is lost and nothing is double-counted.
    """
    if a.card_id != b.card_id:
        raise ValueError("conflict resolution only applies to the same card")
    if a.reviewed_at_ms == b.reviewed_at_ms:
        # Effectively unreachable (revlog ids are unique ms timestamps), but
        # keep it deterministic rather than order-dependent.
        return a if a.ease >= b.ease else b
    return a if a.reviewed_at_ms > b.reviewed_at_ms else b


def revlog_events(col: Collection, card_id: int) -> list[ReviewEvent]:
    """All review events recorded for ``card_id``, oldest first."""
    rows = col.db.all("select id, ease from revlog where cid = ? order by id", card_id)
    return [
        ReviewEvent(card_id=card_id, reviewed_at_ms=int(rid), ease=int(ease))
        for rid, ease in rows
    ]


def last_review_ms(col: Collection, card_id: int) -> int | None:
    """Timestamp (ms) of the most recent review of ``card_id``, or None."""
    val = col.db.scalar("select max(id) from revlog where cid = ?", card_id)
    return int(val) if val is not None else None


# --------------------------------------------------------------------------
# Scoring validation: per-(card, day) dedup (orchestrator contract)
# --------------------------------------------------------------------------


def _collection_day(col: Collection, reviewed_at_ms: int) -> int:
    """Anki collection-relative day number for a revlog id (ms epoch)."""
    return int((reviewed_at_ms / 1000 - col.crt) // 86400)


def raw_graded_review_count(col: Collection, *, deck_filter: str = "1") -> int:
    """Count every graded revlog row (``ease > 0``) — *would* double-count."""
    val = col.db.scalar(
        f"""
        select count(*)
        from revlog r join cards c on r.cid = c.id
        where {deck_filter} and r.ease > 0
        """
    )
    return int(val or 0)


def deduped_graded_review_count(col: Collection, *, deck_filter: str = "1") -> int:
    """Count graded reviews with per-(card, collection-day) dedup.

    The orchestrator's ``compute_cfa_scores`` give-up rule should use this shape
    so a same-card-same-day review made on two devices (which correctly persists
    as two distinct revlog rows after sync) does not inflate graded-review totals.
    """
    rows = col.db.all(
        f"""
        select r.cid, r.id
        from revlog r join cards c on r.cid = c.id
        where {deck_filter} and r.ease > 0
        """
    )
    seen: set[tuple[int, int]] = set()
    for cid, rid in rows:
        seen.add((int(cid), _collection_day(col, int(rid))))
    return len(seen)


def merge_custom_data(col: Collection, card_id: int, namespace: str, payload: dict) -> None:
    """Merge ``payload`` into ``card.custom_data[namespace]`` and save (syncs)."""
    import json

    card = col.get_card(card_id)
    root: dict = {}
    if card.custom_data:
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            parsed = json.loads(card.custom_data)
            if isinstance(parsed, dict):
                root = parsed
    root[namespace] = payload
    serialized = json.dumps(root, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > 100:
        raise ValueError(
            f"custom_data exceeds Anki's 100-byte limit ({len(serialized.encode('utf-8'))} bytes)"
        )
    card.custom_data = serialized
    col.update_card(card)


def compact_ethics_payload(payload: dict) -> dict:
    """Shrink W3 attempt detail to fit Anki's 100-byte ``custom_data`` cap."""
    pid = str(payload.get("pairId") or payload.get("itemId") or "")[:12]
    return {
        "id": pid,
        "ok": bool(payload.get("correct")),
        "hl": str(payload.get("highlight", ""))[:8],
        "src": "ai" if payload.get("source") == "ai" else "fb",
        "std": str(payload.get("standard", ""))[:24],
    }


def read_custom_data_namespace(
    col: Collection, card_id: int, namespace: str
) -> dict | None:
    """Return ``card.custom_data[namespace]`` if present."""
    import json

    card = col.get_card(card_id)
    if not card.custom_data:
        return None
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        parsed = json.loads(card.custom_data)
        if isinstance(parsed, dict) and namespace in parsed:
            val = parsed[namespace]
            return val if isinstance(val, dict) else None
    return None
