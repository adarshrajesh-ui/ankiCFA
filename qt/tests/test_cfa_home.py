# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Increment 2 (desktop-shell): CFA Home is the native landing screen.

Covers the Home payload shape (three honest scores + exam countdown + AI state),
the mediasrv route/endpoint/whitelist wiring, the main-window landing change,
and the CTA bridge routing to the existing CFA entry points. Each assertion
fails on stock ankiCFA (before this increment) and passes after.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import aqt.cfa_home as cfa_home
import aqt.mediasrv as mediasrv
from anki.collection import Collection
from aqt.webview import AnkiWebViewKind

_REPO = Path(__file__).resolve().parents[2]


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def test_home_payload_shape() -> None:
    col = _empty_col()
    try:
        payload = mediasrv._cfa_home_payload(col)
    finally:
        col.close()

    # three honest score bands, each with the shared range/abstain contract
    for key in ("memory", "performance", "readiness"):
        band = payload[key]
        for field in ("abstain", "reason", "point", "rangeLow", "rangeHigh"):
            assert field in band, f"{key} band missing {field}"

    # Home-specific chrome: exam countdown + AI state
    assert "examDate" in payload
    assert "daysToExam" in payload
    assert "aiEnabled" in payload
    assert payload["sync"]["status"] in ("Not connected", "Connected", "Syncing")
    assert "lastSyncedLabel" in payload["sync"]
    assert "actionLabel" in payload["sync"]
    assert payload["heroMode"] in ("abstain", "bayesian_call")


def test_home_ai_flag_reflects_config() -> None:
    col = _empty_col()
    try:
        # AI-first: defaults ON when unset.
        assert mediasrv._cfa_home_payload(col)["aiEnabled"] is True
        col.set_config("cfa_ai_enabled", False)
        assert mediasrv._cfa_home_payload(col)["aiEnabled"] is False
    finally:
        col.close()


def test_home_endpoint_registered_and_served() -> None:
    # POST handler registered -> exposed as /_anki/getCfaHomeView
    assert mediasrv.get_cfa_home_view in mediasrv.post_handler_list
    # route served by mediasrv
    assert mediasrv.is_sveltekit_page("cfa-home") is True
    assert mediasrv.is_sveltekit_page("cfa-home/x") is True
    # whitelisted for the main webview (no API token), like congratsInfo
    src = (_REPO / "qt" / "aqt" / "mediasrv.py").read_text(encoding="utf-8")
    assert '"/_anki/getCfaHomeView"' in src


def test_cfa_shell_routes_and_whitelist_registered() -> None:
    # Concept Map is a first-class main-window tab: its SvelteKit route must be
    # served (otherwise /cfa-concept-map 404s), and it reuses getCfaHomeView so
    # no extra whitelist entry is needed for it.
    assert mediasrv.is_sveltekit_page("cfa-concept-map") is True
    assert mediasrv.is_sveltekit_page("cfa-concept-map/x") is True

    # Readiness and Progress render into the same no-token MAIN webview, so their
    # read-only RPCs must be whitelisted or the pages 403 ("Unexpected API
    # access"). Guard the exact endpoints here.
    src = (_REPO / "qt" / "aqt" / "mediasrv.py").read_text(encoding="utf-8")
    for endpoint in (
        '"/_anki/getCfaExamReadiness"',
        '"/_anki/getGraphPreferences"',
        '"/_anki/graphs"',
        '"/_anki/setGraphPreferences"',
    ):
        assert endpoint in src, f"missing whitelist entry {endpoint}"


def test_cfa_home_webview_kind_has_api_access() -> None:
    assert AnkiWebViewKind.CFA_HOME.value == "cfa home"
    wv_src = (_REPO / "qt" / "aqt" / "webview.py").read_text(encoding="utf-8")
    assert "AnkiWebViewKind.CFA_HOME," in wv_src


def test_landing_moves_to_cfa_home() -> None:
    src = (_REPO / "qt" / "aqt" / "main.py").read_text(encoding="utf-8")
    # the state exists and is dispatched
    assert '"cfaHome"' in src
    assert "_cfaHomeState" in src
    assert "def setupCfaHome" in src
    # profile load lands on CFA Home, not the deck browser
    assert 'self.moveToState("cfaHome")' in src


def test_link_handler_routes_ctas_to_cfa_entry_points(monkeypatch) -> None:
    import aqt.cfa as cfa

    calls: list[str] = []
    monkeypatch.setattr(cfa, "study_ethics_pairs", lambda mw: calls.append("ethics"))
    monkeypatch.setattr(
        cfa, "study_by_exam_priority", lambda mw: calls.append("priority")
    )
    monkeypatch.setattr(
        cfa, "show_exam_readiness", lambda mw: calls.append("readiness")
    )
    monkeypatch.setattr(cfa, "show_deadline", lambda mw: calls.append("deadline"))
    monkeypatch.setattr(cfa_home, "open_ai_settings", lambda mw: calls.append("ai"))
    monkeypatch.setattr(cfa_home, "trigger_cfa_sync", lambda mw: calls.append("sync"))
    monkeypatch.setattr(
        cfa_home, "open_sync_settings", lambda mw: calls.append("sync-settings")
    )

    moved: list[str] = []
    mw = SimpleNamespace(web=object(), moveToState=lambda s: moved.append(s))
    home = cfa_home.CfaHome(mw)  # type: ignore[arg-type]

    for cmd in (
        "cfa:ethics",
        "cfa:priority",
        "cfa:readiness",
        "cfa:conceptmap",
        "cfa:progress",
        "cfa:home",
        "cfa:deadline",
        "cfa:ai",
        "cfa:sync",
        "cfa:sync-settings",
    ):
        home._link_handler(cmd)
    home._link_handler("cfa:decks")

    assert calls == [
        "ethics",
        "priority",
        "readiness",
        "deadline",
        "ai",
        "sync",
        "sync-settings",
    ]
    assert moved == ["cfaConceptMap", "cfaProgress", "cfaHome", "deckBrowser"]


def test_svelte_cfa_cta_commands_have_qt_handlers() -> None:
    ts_files = [
        "ts/lib/cfa/productNav.ts",
        "ts/lib/cfa/pages/home.ts",
        "ts/lib/cfa/pages/CfaHomePage.svelte",
        "ts/lib/cfa/pages/CfaStudyPage.svelte",
        "ts/lib/cfa/pages/readiness.ts",
        "ts/lib/cfa/pages/CfaReadinessPage.svelte",
        "ts/lib/cfa/pages/CfaConceptMapPage.svelte",
    ]
    ts_source = "\n".join(
        (_REPO / path).read_text(encoding="utf-8") for path in ts_files
    )
    cfa_commands = set(re.findall(r'(?:go\(|cmd:\s*)"(cfa:[^"]+)"', ts_source))

    qt_handler_files = [
        "qt/aqt/cfa_home.py",
        "qt/aqt/cfa_study.py",
        "qt/aqt/cfa_readiness.py",
        "qt/aqt/cfa_concept_map.py",
        "qt/aqt/cfa_progress.py",
    ]
    qt_source = "\n".join(
        (_REPO / path).read_text(encoding="utf-8") for path in qt_handler_files
    )
    missing = sorted(cmd for cmd in cfa_commands if cmd not in qt_source)
    assert missing == []

    study_src = (_REPO / "ts/lib/cfa/pages/CfaStudyPage.svelte").read_text(
        encoding="utf-8"
    )
    raw_study_commands = set(re.findall(r'go\("([^"]+)"\)', study_src))
    deck_prefixes = set(re.findall(r'deckCmd\("([^"]+)"', study_src))
    study_handler = (_REPO / "qt/aqt/cfa_study.py").read_text(encoding="utf-8")

    assert {"create-cfa", "import"} <= raw_study_commands
    assert 'cmd in {"create", "create-cfa"}' in study_handler
    assert 'cmd == "import"' in study_handler
    for prefix in deck_prefixes:
        assert f'cmd == "{prefix}"' in study_handler


def test_ethics_show_answer_hook_accepts_card_only(monkeypatch) -> None:
    import aqt
    import aqt.cfa_ethics_sync as cfa_ethics_sync

    card = SimpleNamespace(id=123)
    col = object()
    evals: list[str] = []
    persisted: list[tuple[object, object, dict[str, object]]] = []

    class FakeWeb:
        def evalWithCallback(self, js: str, callback) -> None:  # noqa: N802 - Anki API
            evals.append(js)
            callback('{"completed": true, "score": 1}')

    reviewer = SimpleNamespace(web=FakeWeb(), mw=SimpleNamespace(col=col))
    monkeypatch.setattr(aqt, "mw", SimpleNamespace(reviewer=reviewer), raising=False)
    monkeypatch.setattr(
        cfa_ethics_sync,
        "persist_ethics_attempt",
        lambda col, card, payload: persisted.append((col, card, payload)),
    )

    cfa_ethics_sync._on_show_answer(card)

    assert "cfaEthics:pending" in evals[0]
    assert persisted == [(col, card, {"completed": True, "score": 1})]


def test_shell_state_guard_resets_stale_reviewer_bottom_web() -> None:
    from aqt.main import AnkiQt

    cleared: list[str] = []
    mw = SimpleNamespace(
        _BOTTOM_CHROME_OWNER_STATES=AnkiQt._BOTTOM_CHROME_OWNER_STATES,
        bottomWeb=SimpleNamespace(
            clear_for_shell_state=lambda: cleared.append("clear")
        ),
    )

    AnkiQt._clearBottomChromeIfOrphaned(mw, "cfaHome")  # type: ignore[arg-type]
    AnkiQt._clearBottomChromeIfOrphaned(mw, "review")  # type: ignore[arg-type]

    assert cleared == ["clear"]
