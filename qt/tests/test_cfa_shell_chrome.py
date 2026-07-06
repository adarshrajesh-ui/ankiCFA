# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from __future__ import annotations

# pylint: disable=protected-access
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt.main import AnkiQt
from aqt.toolbar import BottomWebView

_REPO = Path(__file__).resolve().parents[2]


def test_bottom_web_clear_removes_stale_chrome() -> None:
    calls: list[tuple[str, object]] = []
    fake = SimpleNamespace(
        reset_timer=lambda: calls.append(("reset_timer", None)),
        resetHandlers=lambda: calls.append(("resetHandlers", None)),
        stdHtml=lambda body, **kwargs: calls.append(("stdHtml", (body, kwargs))),
        setFixedHeight=lambda height: calls.append(("setFixedHeight", height)),
        web_height=42,
        hidden=True,
    )

    BottomWebView.clear_for_shell_state(fake)  # type: ignore[arg-type]

    assert ("reset_timer", None) in calls
    assert ("resetHandlers", None) in calls
    assert ("stdHtml", ("", {"default_css": False})) in calls
    assert ("setFixedHeight", 0) in calls
    assert fake.web_height == 0
    assert fake.hidden is False


def test_cfa_shell_states_clear_bottom_chrome() -> None:
    cleared: list[str] = []
    mw = SimpleNamespace(
        _BOTTOM_CHROME_OWNER_STATES=AnkiQt._BOTTOM_CHROME_OWNER_STATES,
        bottomWeb=SimpleNamespace(
            clear_for_shell_state=lambda: cleared.append("clear")
        ),
    )

    for state in (
        "cfaHome",
        "cfaStudy",
        "cfaConceptMap",
        "cfaReadiness",
        "cfaProgress",
    ):
        AnkiQt._clearBottomChromeIfOrphaned(mw, state)  # type: ignore[arg-type]

    assert cleared == ["clear"] * 5


def _top_web_fake() -> tuple[SimpleNamespace, list[tuple[str, object]]]:
    calls: list[tuple[str, object]] = []
    fake = SimpleNamespace(
        hidden=False,
        hide_timer=SimpleNamespace(
            stop=lambda: calls.append(("hide_timer.stop", None))
        ),
        reset_timer=lambda: calls.append(("reset_timer", None)),
        setVisible=lambda visible: calls.append(("setVisible", visible)),
        setFixedHeight=lambda height: calls.append(("setFixedHeight", height)),
        setMinimumHeight=lambda height: calls.append(("setMinimumHeight", height)),
        setMaximumHeight=lambda height: calls.append(("setMaximumHeight", height)),
        show=lambda: calls.append(("show", None)),
        adjustHeightToFit=lambda: calls.append(("adjustHeightToFit", None)),
    )
    return fake, calls


def test_cfa_product_states_hide_native_top_toolbar() -> None:
    top, calls = _top_web_fake()
    mw = SimpleNamespace(
        _CFA_PRODUCT_STATES=AnkiQt._CFA_PRODUCT_STATES,
        toolbarWeb=top,
    )

    AnkiQt._syncTopChromeForState(mw, "cfaStudy")  # type: ignore[arg-type]

    assert ("reset_timer", None) in calls
    assert ("hide_timer.stop", None) in calls
    assert ("setVisible", False) in calls
    assert ("setFixedHeight", 0) in calls
    assert top.hidden is True


def test_cfa_progress_keeps_native_top_toolbar() -> None:
    # Progress loads the stock graphs page, which has no in-page CFA product nav.
    # Keep the native CFA toolbar visible so Progress is not a one-way trip.
    top, calls = _top_web_fake()
    top.hidden = True
    mw = SimpleNamespace(
        _CFA_PRODUCT_STATES=AnkiQt._CFA_PRODUCT_STATES,
        toolbarWeb=top,
    )

    AnkiQt._syncTopChromeForState(mw, "cfaProgress")  # type: ignore[arg-type]

    assert ("setVisible", True) in calls
    assert ("show", None) in calls
    assert ("adjustHeightToFit", None) in calls
    assert top.hidden is False


def test_native_states_restore_top_toolbar() -> None:
    top, calls = _top_web_fake()
    top.hidden = True
    mw = SimpleNamespace(
        _CFA_PRODUCT_STATES=AnkiQt._CFA_PRODUCT_STATES,
        toolbarWeb=top,
    )

    AnkiQt._syncTopChromeForState(mw, "review")  # type: ignore[arg-type]

    assert ("setVisible", True) in calls
    assert ("setMinimumHeight", 0) in calls
    assert any(name == "setMaximumHeight" for name, _ in calls)
    assert ("show", None) in calls
    assert ("adjustHeightToFit", None) in calls
    assert top.hidden is False


def test_review_owner_states_keep_bottom_chrome() -> None:
    cleared: list[str] = []
    mw = SimpleNamespace(
        _BOTTOM_CHROME_OWNER_STATES=AnkiQt._BOTTOM_CHROME_OWNER_STATES,
        bottomWeb=SimpleNamespace(
            clear_for_shell_state=lambda: cleared.append("clear")
        ),
    )

    for state in ("deckBrowser", "overview", "review"):
        AnkiQt._clearBottomChromeIfOrphaned(mw, state)  # type: ignore[arg-type]

    assert cleared == []


def test_state_transition_runs_bottom_chrome_guard() -> None:
    src = (_REPO / "qt" / "aqt" / "main.py").read_text(encoding="utf-8")
    assert "self._syncTopChromeForState(state)" in src
    assert "self._clearBottomChromeIfOrphaned(state)" in src
    assert src.index('getattr(self, f"_{state}State"') < src.index(
        "self._syncTopChromeForState(state)"
    )
    assert src.index("self._syncTopChromeForState(state)") < src.index(
        "self._clearBottomChromeIfOrphaned(state)"
    )


def test_cfa_chrome_registered_from_permanent_hooks() -> None:
    src = (_REPO / "qt" / "aqt" / "main.py").read_text(encoding="utf-8")
    assert "from aqt.cfa_chrome import register as register_cfa_chrome" in src
    assert "register_cfa_chrome()" in src
    assert src.index("register_cfa_chrome()") < src.index(
        "hooks.schema_will_change.append"
    )


def test_main_webview_allows_phone_width_shell() -> None:
    src = (_REPO / "qt" / "aqt" / "main.py").read_text(encoding="utf-8")
    assert "self.setMinimumWidth(320)" in src
    assert "self.setMinimumWidth(400)" not in src
