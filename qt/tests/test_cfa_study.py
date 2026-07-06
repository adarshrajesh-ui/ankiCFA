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

import aqt.cfa_study as cfa_study
import aqt.mediasrv as mediasrv
from anki.collection import Collection
from aqt import cfa_chrome, gui_hooks
from aqt.reviewer import Reviewer

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
    assert len(payload["decks"]) == payload["totals"]["activeDecks"]
    for deck in payload["decks"]:
        for field in ("id", "name", "description", "due", "newCount", "mastery"):
            assert field in deck


def test_study_payload_returns_all_decks_ranked_by_urgency(monkeypatch) -> None:
    def row(deck_id: int, name: str, new: int, learn: int, review: int):
        return SimpleNamespace(
            deck_id=deck_id,
            name=name,
            new_count=new,
            learn_count=learn,
            review_count=review,
            children=[],
        )

    root = SimpleNamespace(
        children=[
            row(1, "CFA Delta", 0, 0, 0),
            row(2, "CFA Gamma", 3, 1, 1),
            row(3, "CFA Alpha", 0, 2, 3),
            row(4, "CFA Epsilon", 0, 0, 0),
            row(5, "CFA Beta", 9, 0, 0),
        ]
    )
    col = SimpleNamespace(sched=SimpleNamespace(deck_due_tree=lambda: root))
    monkeypatch.setattr(
        mediasrv,
        "_cfa_home_payload",
        lambda _col: {
            "sync": {},
            "topics": [],
        },
    )

    payload = mediasrv._cfa_study_payload(col)  # type: ignore[arg-type]

    assert [deck["name"] for deck in payload["decks"]] == [
        "CFA Alpha",
        "CFA Beta",
        "CFA Gamma",
        "CFA Delta",
        "CFA Epsilon",
    ]
    assert len(payload["decks"]) == 5
    assert [deck["featured"] for deck in payload["decks"]] == [
        True,
        True,
        True,
        False,
        False,
    ]
    assert payload["selectedDeckId"] == 3


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
    tips: list[str] = []

    class Decks:
        def __init__(self) -> None:
            self.selected: int | None = None

        def select(self, deck_id) -> None:
            self.selected = int(deck_id)

        def id_for_name(self, name: str) -> int | None:
            return 456 if name == "CFA::Ethics Pairs" else None

    due_tree = SimpleNamespace(
        deck_id=0,
        new_count=0,
        learn_count=0,
        review_count=0,
        children=[
            SimpleNamespace(
                deck_id=123,
                new_count=2,
                learn_count=0,
                review_count=0,
                children=[],
            )
        ],
    )
    decks = Decks()
    models = SimpleNamespace(
        by_name=lambda name: {"id": 17} if name == "Basic" else None
    )
    mw = SimpleNamespace(
        web=object(),
        col=SimpleNamespace(
            decks=decks,
            models=models,
            sched=SimpleNamespace(deck_due_tree=lambda: due_tree),
            startTimebox=lambda: calls.append("timebox"),
        ),
        moveToState=moved.append,
        onOverview=lambda: calls.append("overview"),
        onImport=lambda: calls.append("import"),
        reset=lambda: calls.append("reset"),
    )

    monkeypatch.setattr(
        cfa_study,
        "ensure_cfa_study_decks",
        lambda col: calls.append("seed") or {"ethics_added": 30},
    )
    monkeypatch.setattr(cfa_study, "tooltip", lambda msg, **kwargs: tips.append(msg))
    monkeypatch.setattr(
        cfa_study.aqt.dialogs,
        "open",
        lambda name, parent: SimpleNamespace(
            set_deck=lambda deck_id: calls.append(f"add:{int(deck_id)}"),
            set_note_type=lambda notetype_id: calls.append(f"basic:{int(notetype_id)}"),
        ),
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
        "add",
        "create-cfa",
        "create",
        "import",
        "study:not-a-deck",
        "cfa:conceptmap",
        "cfa:home",
        "cfa:readiness",
        "cfa:progress",
        "cfa:sync",
        "cfa:sync-settings",
    ):
        ctrl._link_handler(cmd)

    assert decks.selected == 456
    assert calls == [
        "reset",
        "timebox",
        "add:123",
        "basic:17",
        "seed",
        "add:456",
        "basic:17",
        "seed",
        "reset",
        "seed",
        "reset",
        "import",
        "sync",
        "sync-settings",
    ]
    assert moved == [
        "review",
        "cfaStudy",
        "cfaStudy",
        "cfaConceptMap",
        "cfaHome",
        "cfaReadiness",
        "cfaProgress",
    ]
    assert "overview" not in calls
    assert "That deck link is no longer valid." in tips


def test_study_button_enters_reviewer_without_stock_overview() -> None:
    calls: list[str] = []
    moved: list[str] = []
    due_tree = SimpleNamespace(
        deck_id=123,
        new_count=1,
        learn_count=0,
        review_count=0,
        children=[],
    )
    decks = SimpleNamespace(
        select=lambda deck_id: calls.append(f"select:{int(deck_id)}")
    )
    mw = SimpleNamespace(
        web=object(),
        col=SimpleNamespace(
            decks=decks,
            sched=SimpleNamespace(deck_due_tree=lambda: due_tree),
            startTimebox=lambda: calls.append("timebox"),
        ),
        moveToState=moved.append,
        onOverview=lambda: calls.append("overview"),
        reset=lambda: calls.append("reset"),
    )

    cfa_study.CfaStudy(mw)._link_handler("study:123")  # type: ignore[arg-type]

    assert calls == ["select:123", "reset", "timebox"]
    assert moved == ["review"]
    assert "overview" not in calls


def test_study_button_initializes_cfa_reviewer_contexts(monkeypatch) -> None:
    calls: list[str] = []
    moved: list[str] = []
    rendered: list[tuple[str, str, SimpleNamespace]] = []
    gui_hooks.webview_will_set_content.remove(cfa_chrome.on_webview_will_set_content)
    gui_hooks.card_will_show.remove(cfa_chrome.on_card_will_show)
    monkeypatch.setattr(cfa_chrome, "_registered", False)
    due_tree = SimpleNamespace(
        deck_id=123,
        new_count=1,
        learn_count=0,
        review_count=0,
        children=[],
    )

    class CapturingWeb:
        allow_drops: bool = False

        def __init__(self, name: str) -> None:
            self.name = name

        def stdHtml(self, body: str, **kwargs) -> None:
            context = kwargs.get("context")
            wc = SimpleNamespace(head=kwargs.get("head", ""), body=body)
            gui_hooks.webview_will_set_content(wc, context)
            rendered.append((self.name, type(context).__name__, wc))

        def eval(self, script: str) -> None:
            calls.append(f"{self.name}:eval")

    class Decks:
        def select(self, deck_id) -> None:
            calls.append(f"select:{int(deck_id)}")

        def name_if_exists(self, deck_id) -> str:
            return "Default"

        def name(self, deck_id) -> str:
            return "Default"

    reviewer = Reviewer.__new__(Reviewer)
    main_web = CapturingWeb("main")
    bottom_web = CapturingWeb("bottom")
    mw = SimpleNamespace(
        web=object(),
        pm=SimpleNamespace(video_driver=lambda: "auto"),
        col=SimpleNamespace(
            conf={"reviewExtra": ""},
            decks=Decks(),
            sched=SimpleNamespace(deck_due_tree=lambda: due_tree),
            startTimebox=lambda: calls.append("timebox"),
        ),
        reset=lambda: calls.append("reset"),
    )
    reviewer.mw = mw
    reviewer.web = main_web
    reviewer.bottom = SimpleNamespace(web=bottom_web)
    reviewer.card = SimpleNamespace(time_taken=lambda: 0)
    monkeypatch.setattr(
        Reviewer,
        "revHtml",
        lambda self: '<div id="qa" dir="auto"></div>',
    )
    monkeypatch.setattr(
        Reviewer,
        "_bottomHTML",
        lambda self: "<center id=outer><table id=innertable></table></center>",
    )

    def move_to_state(state: str) -> None:
        moved.append(state)
        if state == "review":
            Reviewer._initWeb(reviewer)

    mw.moveToState = move_to_state
    monkeypatch.setattr(cfa_chrome.aqt, "mw", mw, raising=False)

    cfa_study.CfaStudy(mw)._link_handler("study:123")  # type: ignore[arg-type]

    assert calls[:3] == ["select:123", "reset", "timebox"]
    assert moved == ["review"]
    assert getattr(mw, "_cfa_review_from_study") is True
    assert any(
        name == "main"
        and context_name == "Reviewer"
        and "cfa-chrome-reviewer" in wc.head
        for name, context_name, wc in rendered
    )
    assert any(
        name == "bottom"
        and context_name == "ReviewerBottomBar"
        and "cfa-chrome-reviewer-bottom" in wc.head
        for name, context_name, wc in rendered
    )

    card = SimpleNamespace(
        current_deck_id=lambda: 123,
        note_type=lambda: {"name": "CFA Knowledge"},
    )
    html = gui_hooks.card_will_show("Plain CFA Knowledge", card, "reviewQuestion")
    assert "cfa-basic-review-card cfa-basic-review-card--question" in html
    assert "Plain CFA Knowledge" in html


def test_study_deck_with_nothing_ready_stays_on_cfa_study(monkeypatch) -> None:
    calls: list[str] = []
    moved: list[str] = []
    tips: list[str] = []
    due_tree = SimpleNamespace(
        deck_id=123,
        new_count=0,
        learn_count=0,
        review_count=0,
        children=[],
    )
    decks = SimpleNamespace(
        select=lambda deck_id: calls.append(f"select:{int(deck_id)}"),
        card_count=lambda deck_id, include_subdecks: 0,
    )
    mw = SimpleNamespace(
        web=object(),
        col=SimpleNamespace(
            decks=decks,
            sched=SimpleNamespace(deck_due_tree=lambda: due_tree),
            startTimebox=lambda: calls.append("timebox"),
        ),
        moveToState=moved.append,
        onOverview=lambda: calls.append("overview"),
        reset=lambda: calls.append("reset"),
    )
    monkeypatch.setattr(cfa_study, "tooltip", lambda msg, **kwargs: tips.append(msg))

    cfa_study.CfaStudy(mw)._link_handler("study:123")  # type: ignore[arg-type]

    assert calls == ["select:123", "reset"]
    assert moved == ["cfaStudy"]
    assert "overview" not in calls
    assert "review" not in moved
    assert tips == ["No cards are ready in this deck. Add cards or import CFA notes."]


def test_study_add_cards_selects_basic_note_type(monkeypatch) -> None:
    captured: dict[str, object] = {}

    add_cards = SimpleNamespace(
        set_deck=lambda deck_id: captured.setdefault("deck", int(deck_id)),
        set_note_type=lambda notetype_id: captured.setdefault(
            "notetype", int(notetype_id)
        ),
    )
    decks = SimpleNamespace(id_for_name=lambda name: 456)
    models = SimpleNamespace(
        by_name=lambda name: {"id": 17} if name == "Basic" else None
    )
    mw = SimpleNamespace(web=object(), col=SimpleNamespace(decks=decks, models=models))

    monkeypatch.setattr(cfa_study, "ensure_cfa_study_decks", lambda _col: {})
    monkeypatch.setattr(cfa_study.aqt.dialogs, "open", lambda name, parent: add_cards)

    cfa_study.CfaStudy(mw)._link_handler("add")  # type: ignore[arg-type]

    assert captured["deck"] == 456
    assert captured["notetype"] == 17


def test_study_add_cards_gracefully_skips_missing_basic(monkeypatch) -> None:
    captured: dict[str, object] = {}

    add_cards = SimpleNamespace(
        set_deck=lambda deck_id: captured.setdefault("deck", int(deck_id)),
        set_note_type=lambda notetype_id: captured.setdefault(
            "notetype", int(notetype_id)
        ),
    )
    models = SimpleNamespace(by_name=lambda name: None)
    mw = SimpleNamespace(
        web=object(),
        col=SimpleNamespace(
            decks=SimpleNamespace(id_for_name=lambda name: 456), models=models
        ),
    )

    monkeypatch.setattr(cfa_study, "ensure_cfa_study_decks", lambda _col: {})
    monkeypatch.setattr(cfa_study.aqt.dialogs, "open", lambda name, parent: add_cards)

    cfa_study.CfaStudy(mw)._link_handler("add")  # type: ignore[arg-type]

    assert captured == {"deck": 456}


def test_study_add_cards_reports_native_gap_without_crashing(monkeypatch) -> None:
    tips: list[str] = []
    mw = SimpleNamespace(
        web=object(),
        col=SimpleNamespace(
            decks=SimpleNamespace(id_for_name=lambda name: 456),
            models=SimpleNamespace(by_name=lambda name: {"id": 17}),
        ),
    )

    monkeypatch.setattr(cfa_study, "ensure_cfa_study_decks", lambda _col: {})
    monkeypatch.setattr(
        cfa_study.aqt.dialogs,
        "open",
        lambda name, parent: (_ for _ in ()).throw(RuntimeError("native gap")),
    )
    monkeypatch.setattr(cfa_study, "tooltip", lambda msg, **kwargs: tips.append(msg))

    cfa_study.CfaStudy(mw)._link_handler("add")  # type: ignore[arg-type]

    assert tips == [
        "Use Anki's native Add Cards screen to add CFA cards on this device."
    ]


def test_study_import_reports_native_gap_without_crashing(monkeypatch) -> None:
    tips: list[str] = []
    mw = SimpleNamespace(web=object(), col=object())
    monkeypatch.setattr(cfa_study, "tooltip", lambda msg, **kwargs: tips.append(msg))

    cfa_study.CfaStudy(mw)._link_handler("import")  # type: ignore[arg-type]

    assert tips == [
        "Use Anki's native Import action to bring CFA notes onto this device."
    ]
