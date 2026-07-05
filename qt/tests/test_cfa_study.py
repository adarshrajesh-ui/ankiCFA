# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Study deck-first workspace guards."""

# pylint: disable=protected-access

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from anki.collection import Collection

import aqt.cfa_study as cfa_study
import aqt.mediasrv as mediasrv

_REPO = Path(__file__).resolve().parents[2]


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def test_study_endpoint_registered_and_served() -> None:
    assert mediasrv.get_cfa_study_view in mediasrv.post_handler_list
    assert mediasrv.is_sveltekit_page("cfa-study") is True
    assert mediasrv.is_sveltekit_page("cfa-study/x") is True
    src = (_REPO / "qt" / "aqt" / "mediasrv.py").read_text(encoding="utf-8")
    assert '"/_anki/getCfaStudyView"' in src


def test_study_payload_shape_uses_existing_deck_tree() -> None:
    col = _empty_col()
    try:
        payload = mediasrv._cfa_study_payload(col)
    finally:
        col.close()

    assert set(payload) == {"sync", "totals", "decks", "selectedDeckId", "footerText"}
    assert payload["totals"]["activeDecks"] >= 1
    assert len(payload["decks"]) <= 3
    for deck in payload["decks"]:
        for field in ("id", "name", "description", "due", "newCount", "mastery"):
            assert field in deck


def test_study_state_and_toolbar_are_registered() -> None:
    main_src = (_REPO / "qt" / "aqt" / "main.py").read_text(encoding="utf-8")
    toolbar_src = (_REPO / "qt" / "aqt" / "toolbar.py").read_text(encoding="utf-8")
    assert '"cfaStudy"' in main_src
    assert "_cfaStudyState" in main_src
    assert "def setupCfaStudy" in main_src
    assert '"cfaStudy": "cfa_study"' in toolbar_src
    assert 'self.mw.moveToState("cfaStudy")' in toolbar_src


def test_study_link_handler_routes_existing_flows(monkeypatch) -> None:
    calls: list[str] = []
    moved: list[str] = []

    class Decks:
        def __init__(self) -> None:
            self.selected: int | None = None

        def select(self, deck_id) -> None:
            self.selected = int(deck_id)

        def current(self) -> dict[str, str]:
            return {"name": "CFA Level II"}

    decks = Decks()
    mw = SimpleNamespace(
        web=object(),
        col=SimpleNamespace(decks=decks),
        moveToState=moved.append,
        onOverview=lambda: calls.append("overview"),
        onImport=lambda: calls.append("import"),
    )

    monkeypatch.setattr(cfa_study, "add_deck_dialog", lambda **kwargs: SimpleNamespace(run_in_background=lambda: calls.append("create")))
    monkeypatch.setattr(
        cfa_study.aqt.dialogs,
        "open",
        lambda name, parent: SimpleNamespace(set_deck=lambda deck_id: calls.append(f"add:{int(deck_id)}")),
    )
    monkeypatch.setattr(
        "aqt.cfa_home.trigger_cfa_sync",
        lambda mw: calls.append("sync"),
    )
    monkeypatch.setattr(
        "aqt.cfa_home.open_sync_settings",
        lambda mw: calls.append("sync-settings"),
    )

    ctrl = cfa_study.CfaStudy(mw)  # type: ignore[arg-type]
    for cmd in (
        "study:123",
        "add:123",
        "create",
        "import",
        "cfa:conceptmap",
        "cfa:readiness",
        "cfa:sync",
        "cfa:sync-settings",
    ):
        ctrl._link_handler(cmd)

    assert decks.selected == 123
    assert calls == ["overview", "add:123", "create", "import", "sync", "sync-settings"]
    assert moved == ["cfaConceptMap", "cfaReadiness"]
