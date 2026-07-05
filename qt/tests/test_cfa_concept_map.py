# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Concept Map route and bridge guards."""

# pylint: disable=protected-access

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import aqt.cfa as cfa
import aqt.cfa_concept_map as cfa_concept_map
import aqt.mediasrv as mediasrv


def test_concept_map_route_is_first_class_sveltekit_page() -> None:
    assert mediasrv.is_sveltekit_page("cfa-concept-map") is True
    assert mediasrv.is_sveltekit_page("cfa-concept-map/x") is True


def test_concept_map_link_handler_routes_existing_flows(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cfa, "study_by_exam_priority", lambda mw: calls.append("priority"))
    monkeypatch.setattr(cfa, "study_ethics_pairs", lambda mw: calls.append("ethics"))
    monkeypatch.setattr(cfa, "show_exam_readiness", lambda mw: calls.append("readiness"))

    moved: list[str] = []
    mw = SimpleNamespace(web=object(), moveToState=moved.append)
    ctrl = cfa_concept_map.CfaConceptMap(mw)  # type: ignore[arg-type]

    for cmd in ("cfa:priority", "cfa:ethics", "cfa:readiness"):
        ctrl._link_handler(cmd)
    ctrl._link_handler("cfa:home")
    ctrl._link_handler("cfa:decks")

    assert calls == ["priority", "ethics", "readiness"]
    assert moved == ["cfaHome", "deckBrowser"]
