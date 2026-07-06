# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA internal state storage — app-only state that rides normal Anki sync.

CFA study data (flashcards, ethics cards, revlog, FSRS state, note tags,
decks) and small global settings (``cfa_exam_config``, AI toggles) already sync
natively: the first as ordinary collection objects, the second through
``col.conf``. What was missing was a home for *larger, CFA-app-only* state that
is neither a card nor a tiny config flag — e.g. cached Concept-Map AI
explanation batches, a pinned layout, or user watchlist overrides.

Rather than stand up a custom sync server for that, this module stores such
state as **suspended notes in a dedicated internal deck** (:data:`INTERNAL_DECK_NAME`)
using a dedicated notetype (:data:`STATE_NOTETYPE_NAME`). Notes, cards and
their fields all travel through Anki's own sync engine, so the state reaches
every device for free.

Design guarantees:

* The internal deck's cards are **suspended on creation** and the deck is given
  a zero-limit config, so they never enter the study queue.
* Internal notes carry **no** ``los::`` topic tags and are never reviewed, so
  they contribute nothing to the memory / performance / readiness scores, which
  key on ``los::`` topics and graded revlog rows.
* CFA deck listings must exclude :data:`INTERNAL_DECK_NAME` (see
  :func:`is_internal_deck_name`) so the user never studies or sees it as CFA
  study material.

Everything here is idempotent and safe to re-run after a sync.
"""

from __future__ import annotations

import contextlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

import anki.collection
from anki.decks import DeckId
from anki.notes import NoteId

# The internal, never-studied deck. Namespaced under "CFA::" so it groups with
# the other CFA decks; the leading underscore marks it as machine-owned.
INTERNAL_DECK_NAME = "CFA::_Internal"
# A dedicated deck config with zero new/review limits (belt-and-suspenders on
# top of per-card suspension), so the deck can never surface study material.
INTERNAL_DECK_CONFIG_NAME = "CFA Internal (no study)"

# The state-record notetype. Field order is significant: ``Key`` is the sort
# field and the lookup key; ``Payload`` holds compact JSON.
STATE_NOTETYPE_NAME = "CFA State Record"
TEMPLATE_NAME = "State"
FIELDS = ["Key", "Payload", "SchemaVersion", "UpdatedAt"]
DEFAULT_SCHEMA_VERSION = 1

# Minimal but valid template (front must reference a field). These cards are
# suspended and the deck is excluded from study, so this only ever renders if a
# user deliberately opens the record in the stock Browser.
_FRONT = "{{Key}}"
_BACK = "{{FrontSide}}\n<hr id=answer>\n{{Payload}}"
_CSS = ".card{font-family:monospace;white-space:pre-wrap;text-align:left;}"


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


# --------------------------------------------------------------------------
# Idempotent storage setup
# --------------------------------------------------------------------------


def _ensure_state_notetype(col: anki.collection.Collection) -> Any:
    """Create the ``CFA State Record`` notetype if missing; refresh it if present."""
    existing = col.models.by_name(STATE_NOTETYPE_NAME)
    if existing is not None:
        present = {f["name"] for f in existing["flds"]}
        changed = False
        for name in FIELDS:
            if name not in present:
                col.models.add_field(existing, col.models.new_field(name))
                changed = True
        if changed:
            col.models.update_dict(existing)
            return col.models.by_name(STATE_NOTETYPE_NAME)
        return existing

    nt = col.models.new(STATE_NOTETYPE_NAME)
    for name in FIELDS:
        col.models.add_field(nt, col.models.new_field(name))
    col.models.set_sort_index(nt, 0)  # sort by Key

    tmpl = col.models.new_template(TEMPLATE_NAME)
    tmpl["qfmt"] = _FRONT
    tmpl["afmt"] = _BACK
    col.models.add_template(nt, tmpl)
    nt["css"] = _CSS

    col.models.add(nt)
    return col.models.by_name(STATE_NOTETYPE_NAME)


def _apply_no_study_config(col: anki.collection.Collection, did: DeckId) -> None:
    """Give the internal deck a zero-limit deck config so it never studies."""
    conf = None
    for candidate in col.decks.all_config():
        if candidate.get("name") == INTERNAL_DECK_CONFIG_NAME:
            conf = candidate
            break
    if conf is None:
        conf = col.decks.add_config(INTERNAL_DECK_CONFIG_NAME)
    conf["new"]["perDay"] = 0
    conf["rev"]["perDay"] = 0
    col.decks.update_config(conf)

    deck = col.decks.get(did, default=False)
    if deck is not None and str(deck.get("conf")) != str(conf["id"]):
        col.decks.set_config_id_for_deck_dict(deck, conf["id"])


def _ensure_internal_deck(col: anki.collection.Collection) -> DeckId:
    did = DeckId(int(col.decks.id(INTERNAL_DECK_NAME)))
    # Zero-limit config is a nicety on top of per-card suspension; never let a
    # config hiccup block storage (suspension is the real guarantee).
    with contextlib.suppress(Exception):
        _apply_no_study_config(col, did)
    return did


def ensure_cfa_internal_storage(
    col: anki.collection.Collection,
) -> tuple[DeckId, Any]:
    """Idempotently ensure the internal deck + notetype exist.

    Returns ``(deck_id, notetype_dict)``. Safe to call on every launch and after
    every sync — it creates nothing that already exists.
    """
    nt = _ensure_state_notetype(col)
    did = _ensure_internal_deck(col)
    return did, nt


# --------------------------------------------------------------------------
# Deck-exclusion helpers (keep internal cards out of study / counts / scores)
# --------------------------------------------------------------------------


def is_internal_deck_name(name: str) -> bool:
    """True for the internal deck or any subdeck of it."""
    return name == INTERNAL_DECK_NAME or name.startswith(INTERNAL_DECK_NAME + "::")


def internal_deck_ids(col: anki.collection.Collection) -> list[DeckId]:
    """Deck ids for the internal deck and its children (empty if not created)."""
    did = col.decks.id_for_name(INTERNAL_DECK_NAME)
    if did is None:
        return []
    ids = [DeckId(int(did))]
    ids.extend(DeckId(int(cid)) for _name, cid in col.decks.children(DeckId(int(did))))
    return ids


# --------------------------------------------------------------------------
# Generic state-record CRUD (compact JSON payloads, schema-versioned)
# --------------------------------------------------------------------------


def _find_state_note(col: anki.collection.Collection, key: str) -> Any:
    """Return the note whose ``Key`` field equals ``key``, or None.

    Matches in Python rather than via a field search so arbitrary keys need no
    query escaping; the internal record set is tiny, so this is cheap.
    """
    if col.models.by_name(STATE_NOTETYPE_NAME) is None:
        return None
    for nid in col.find_notes(f'note:"{STATE_NOTETYPE_NAME}"'):
        note = col.get_note(nid)
        if note["Key"] == key:
            return note
    return None


def upsert_cfa_state_record(
    col: anki.collection.Collection,
    key: str,
    payload: Any,
    *,
    schema_version: int = DEFAULT_SCHEMA_VERSION,
) -> NoteId:
    """Create or update the internal state record for ``key``.

    ``payload`` is stored as compact JSON. Writes are idempotent and safe after
    sync: the record is keyed by ``Key`` and updated in place when it already
    exists. New records are added to the internal deck and their card suspended
    immediately so they never enter study.
    """
    did, nt = ensure_cfa_internal_storage(col)
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    now = _now_iso()

    note = _find_state_note(col, key)
    if note is not None:
        note["Payload"] = serialized
        note["SchemaVersion"] = str(schema_version)
        note["UpdatedAt"] = now
        col.update_note(note)
        return NoteId(int(note.id))

    note = col.new_note(nt)
    note["Key"] = key
    note["Payload"] = serialized
    note["SchemaVersion"] = str(schema_version)
    note["UpdatedAt"] = now
    col.add_note(note, DeckId(int(did)))

    cids = list(col.find_cards(f"nid:{note.id}"))
    if cids:
        with contextlib.suppress(Exception):
            col.sched.suspend_cards(cids)
    return NoteId(int(note.id))


def get_cfa_state_record(col: anki.collection.Collection, key: str) -> Optional[Any]:
    """Return the decoded payload for ``key``, or None when absent/undecodable."""
    note = _find_state_note(col, key)
    if note is None:
        return None
    raw = note["Payload"]
    if not raw:
        return None
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        return json.loads(raw)
    return None


def delete_cfa_state_record(col: anki.collection.Collection, key: str) -> int:
    """Delete the record(s) for ``key``. Returns how many notes were removed."""
    if col.models.by_name(STATE_NOTETYPE_NAME) is None:
        return 0
    nids = [
        nid
        for nid in col.find_notes(f'note:"{STATE_NOTETYPE_NAME}"')
        if col.get_note(nid)["Key"] == key
    ]
    if nids:
        col.remove_notes(nids)
    return len(nids)


def list_cfa_state_records(
    col: anki.collection.Collection,
) -> dict[str, Optional[Any]]:
    """Return ``{key: decoded_payload}`` for every internal state record."""
    out: dict[str, Optional[Any]] = {}
    if col.models.by_name(STATE_NOTETYPE_NAME) is None:
        return out
    for nid in col.find_notes(f'note:"{STATE_NOTETYPE_NAME}"'):
        note = col.get_note(nid)
        raw = note["Payload"]
        value: Optional[Any] = None
        if raw:
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                value = json.loads(raw)
        out[note["Key"]] = value
    return out


__all__ = [
    "INTERNAL_DECK_NAME",
    "INTERNAL_DECK_CONFIG_NAME",
    "STATE_NOTETYPE_NAME",
    "FIELDS",
    "DEFAULT_SCHEMA_VERSION",
    "ensure_cfa_internal_storage",
    "is_internal_deck_name",
    "internal_deck_ids",
    "upsert_cfa_state_record",
    "get_cfa_state_record",
    "delete_cfa_state_record",
    "list_cfa_state_records",
]
