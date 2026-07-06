# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Part 1: the desktop startup refresh of baked ethics notetype templates.

The ethics card templates (``qfmt``/``afmt``/``css``) are baked into the
collection's notetype at seed/import time and never refreshed afterward, so an
on-disk template fix never reaches a collection that already has the ethics deck.
``aqt.cfa.refresh_ethics_templates`` (wired to ``collection_did_load``) fixes
that by refreshing BOTH ethics notetypes in place from the current on-disk
templates — but only when they already exist, so a fresh profile is still seeded
by the normal first-launch path (it must never force-create empty content here).

These tests exercise the refresh directly against a real collection and confirm:
the baked ``qfmt`` is updated to match the current disk template; a fresh profile
is left untouched (no force-create); notes/notetypes are never duplicated; and
the refresh is actually wired to the collection-load event desktop startup fires.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ethics_notetype / passages are the fork's ethics_pairs sources. Make that
# directory importable even under the plain ``qt/tests`` gate, which (unlike the
# ``just cfa-*`` recipes) does not put ``cfa/ethics_pairs`` on PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cfa" / "ethics_pairs"))

import ethics_notetype
import passages

from anki.collection import Collection
from aqt import cfa

_REPO = Path(__file__).resolve().parents[2]
_TEMPLATES = _REPO / "cfa" / "ethics_pairs" / "templates"

# Stand-ins for the out-of-date baked templates an existing collection actually
# has. The backend rejects a front template with no field replacement, so the
# sentinels embed a valid ``{{Field}}`` while staying clearly distinct from the
# real (much larger) on-disk templates that the refresh must restore.
_STALE_CSS = "/* STALE baked css - should be overwritten from disk */"


def _stale_tmpl(label: str, field: str) -> str:
    return "<!-- STALE " + label + " (pre-refresh) --><br>{{" + field + "}}"


def _disk(name: str) -> str:
    return (_TEMPLATES / name).read_text(encoding="utf-8")


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def test_startup_refresh_updates_baked_minimal_pair_qfmt() -> None:
    col = _empty_col()
    try:
        # Simulate a collection that already imported the ethics deck, then had
        # its baked template go stale (the real-world state before this fix).
        ethics_notetype.ensure_notetype(col)
        nt = col.models.by_name(ethics_notetype.NOTETYPE_NAME)
        assert nt is not None
        stale_qfmt = _stale_tmpl("minimal-pair front", "PairId")
        nt["tmpls"][0]["qfmt"] = stale_qfmt
        nt["tmpls"][0]["afmt"] = _stale_tmpl("minimal-pair back", "Rationale")
        nt["css"] = _STALE_CSS
        col.models.update_dict(nt)
        # Precondition: the stale template is really persisted.
        stored = col.models.by_name(ethics_notetype.NOTETYPE_NAME)
        assert stored["tmpls"][0]["qfmt"] == stale_qfmt

        cfa.refresh_ethics_templates(col)

        refreshed = col.models.by_name(ethics_notetype.NOTETYPE_NAME)
        assert refreshed["tmpls"][0]["qfmt"] == _disk("front.html")
        assert refreshed["tmpls"][0]["afmt"] == _disk("back.html")
        assert refreshed["css"] == _disk("style.css")
    finally:
        col.close()


def test_startup_refresh_updates_baked_passage_qfmt() -> None:
    col = _empty_col()
    try:
        passages.ensure_notetype(col)
        nt = col.models.by_name(passages.NOTETYPE_NAME)
        assert nt is not None
        nt["tmpls"][0]["qfmt"] = _stale_tmpl("passage front", "Passage")
        nt["tmpls"][0]["afmt"] = _stale_tmpl("passage back", "Rationale")
        col.models.update_dict(nt)

        cfa.refresh_ethics_templates(col)

        refreshed = col.models.by_name(passages.NOTETYPE_NAME)
        assert refreshed["tmpls"][0]["qfmt"] == _disk("passage_front.html")
        assert refreshed["tmpls"][0]["afmt"] == _disk("passage_back.html")
    finally:
        col.close()


def test_startup_refresh_does_not_create_when_absent() -> None:
    col = _empty_col()
    try:
        # Fresh profile: neither ethics notetype exists yet. The refresh MUST be
        # a no-op — the first-launch seeder (not this refresh) creates them, so
        # force-creating here would bake empty content before the seeder runs.
        cfa.refresh_ethics_templates(col)
        assert col.models.by_name(ethics_notetype.NOTETYPE_NAME) is None
        assert col.models.by_name(passages.NOTETYPE_NAME) is None
    finally:
        col.close()


def test_startup_refresh_does_not_duplicate_notes_or_notetype() -> None:
    col = _empty_col()
    try:
        ethics_notetype.ensure_notetype(col)
        nt = col.models.by_name(ethics_notetype.NOTETYPE_NAME)
        original_id = nt["id"]
        deck_id = col.decks.id(ethics_notetype.DECK_NAME)
        note = col.new_note(nt)
        note["PairId"] = "pair-1"
        col.add_note(note, deck_id)
        notes_before = col.note_count()

        cfa.refresh_ethics_templates(col)

        # Same single notetype (refreshed in place, not re-created) and the note
        # count is untouched — the refresh never seeds or duplicates.
        after = col.models.by_name(ethics_notetype.NOTETYPE_NAME)
        assert after["id"] == original_id
        assert col.note_count() == notes_before
    finally:
        col.close()


def test_startup_refresh_is_wired_to_collection_load() -> None:
    from aqt import gui_hooks

    # Registration is idempotent, and it hooks the exact event desktop startup
    # fires (aqt.main.loadCollection -> gui_hooks.collection_did_load).
    cfa._register_ethics_template_refresh()
    cfa._register_ethics_template_refresh()
    assert cfa.refresh_ethics_templates in gui_hooks.collection_did_load._hooks
    assert gui_hooks.collection_did_load._hooks.count(cfa.refresh_ethics_templates) == 1

    col = _empty_col()
    try:
        ethics_notetype.ensure_notetype(col)
        nt = col.models.by_name(ethics_notetype.NOTETYPE_NAME)
        nt["tmpls"][0]["qfmt"] = _stale_tmpl("minimal-pair front", "PairId")
        col.models.update_dict(nt)

        # Fire the load hook exactly as the main window does on profile open.
        gui_hooks.collection_did_load(col)

        refreshed = col.models.by_name(ethics_notetype.NOTETYPE_NAME)
        assert refreshed["tmpls"][0]["qfmt"] == _disk("front.html")
    finally:
        col.close()
