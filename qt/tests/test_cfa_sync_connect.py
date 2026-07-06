# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Fix CFA Sync (desktop): endpoint healing, sync-result clarity, and the
fresh-account conflict/reload contract.

These are pure-Python unit tests over ``aqt.cfa_sync_connect`` (mocked ``mw``/
``pm``), so they need neither a real profile nor a live sync server. They pin:

* endpoint healing now clears a stale loopback ``currentSyncUrl`` (not just
  ``customSyncUrl``) while leaving a legitimate self-host endpoint intact;
* the Home/sync status payload carries a plain, account-aware post-sync result
  ("Synced as <account>" / "Already up to date");
* the CFA sync wrappers delegate to Anki's own sync (which surfaces the
  standard first-sync download-vs-upload conflict dialog) and reload the open
  CFA screen after a sync (including a full download) via ``sync_did_finish``.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt import cfa_sync_connect as cc

_REPO = Path(__file__).resolve().parents[2]


class _PM:
    """A minimal profile-manager stand-in that mirrors profiles.py semantics.

    In particular ``set_custom_sync_url`` also clears ``currentSyncUrl`` when the
    value changes, exactly like ``aqt.profiles.ProfileManager``.
    """

    def __init__(self, custom: str | None = None, current: str | None = None) -> None:
        self._custom = custom
        self._current = current

    def custom_sync_url(self) -> str | None:
        return self._custom

    def set_custom_sync_url(self, url: str | None) -> None:
        if url != self._custom:
            self._current = None
            self._custom = url

    def _current_sync_url(self) -> str | None:
        return self._current

    def set_current_sync_url(self, url: str | None) -> None:
        self._current = url


# --- desktop-endpoint-heal ---------------------------------------------------


def test_heal_clears_loopback_current_sync_url() -> None:
    # A leftover loopback ``currentSyncUrl`` (from an old dev build) with no
    # custom URL is the primary "sync is dead" bug: sync_endpoint() returns it
    # first, so every sync hits a dead 127.0.0.1 server. Healing clears it.
    pm = _PM(custom=None, current="http://127.0.0.1:27701/")
    mw = SimpleNamespace(pm=pm)
    assert cc.heal_stale_local_sync_url(mw) is True
    assert pm._current is None
    assert pm._custom is None
    # Idempotent: a second heal is a no-op now that the endpoint is clean.
    assert cc.heal_stale_local_sync_url(mw) is False


def test_heal_clears_loopback_current_but_keeps_legit_custom() -> None:
    # The exact bug the plan calls out: a legitimate self-host custom server
    # with a stale loopback ``currentSyncUrl`` redirect. Only the loopback
    # current slot is cleared; the real endpoint survives.
    pm = _PM(custom="https://sync.example.com/", current="http://127.0.0.1:27701/")
    assert cc.heal_stale_local_sync_url(SimpleNamespace(pm=pm)) is True
    assert pm._custom == "https://sync.example.com/"
    assert pm._current is None


def test_heal_leaves_legitimate_non_loopback_endpoint_intact() -> None:
    # A genuine self-hosted server in BOTH slots is never touched.
    pm = _PM(custom="https://sync.example.com/", current="https://sync.example.com/x")
    assert cc.heal_stale_local_sync_url(SimpleNamespace(pm=pm)) is False
    assert pm._custom == "https://sync.example.com/"
    assert pm._current == "https://sync.example.com/x"

    # AnkiWeb default (both slots empty) is a no-op.
    empty = _PM(custom=None, current=None)
    assert cc.heal_stale_local_sync_url(SimpleNamespace(pm=empty)) is False


def test_heal_is_exception_safe_without_current_url_api() -> None:
    # Backward-compat: a pm exposing only the custom-url API (no
    # _current_sync_url) must still heal the custom slot without raising.
    class LegacyPM:
        def __init__(self, url: str | None) -> None:
            self.url = url

        def custom_sync_url(self) -> str | None:
            return self.url

        def set_custom_sync_url(self, url: str | None) -> None:
            self.url = url

    pm = LegacyPM("http://localhost:27701/")
    assert cc.heal_stale_local_sync_url(SimpleNamespace(pm=pm)) is True
    assert pm.url is None
    assert cc.heal_stale_local_sync_url(None) is False


def _fake_hook() -> object:
    class FakeHook:
        def __init__(self) -> None:
            self.callbacks: list = []

        def append(self, cb) -> None:
            self.callbacks.append(cb)

    return FakeHook()


def test_register_endpoint_healing_hooks_collection_load(monkeypatch) -> None:
    import aqt.gui_hooks as gh

    fake = _fake_hook()
    monkeypatch.setattr(gh, "collection_did_load", fake)
    monkeypatch.setattr(cc, "_ENDPOINT_HEAL_REGISTERED", False)

    healed: list = []
    monkeypatch.setattr(cc, "heal_stale_local_sync_url", lambda mw: healed.append(mw))

    mw = object()
    cc.register_endpoint_healing(mw)  # type: ignore[arg-type]
    assert len(fake.callbacks) == 1  # type: ignore[attr-defined]

    # Firing the hook (as collection load does) heals the endpoint — so the
    # auto-sync-on-open that follows targets AnkiWeb, not a dead loopback.
    fake.callbacks[0](object())  # type: ignore[attr-defined]
    assert healed == [mw]

    # Idempotent registration: a second call adds no further hook.
    cc.register_endpoint_healing(mw)  # type: ignore[arg-type]
    assert len(fake.callbacks) == 1  # type: ignore[attr-defined]


# --- sync-result-clarity -----------------------------------------------------


def _status(profile: dict, endpoint: str | None) -> dict:
    class PM:
        def __init__(self) -> None:
            self.profile = profile

        def sync_auth(self):
            return object() if profile.get("syncUser") else None

        def sync_endpoint(self):
            return endpoint

    return cc.sync_status_payload(SimpleNamespace(pm=PM()))


def test_result_label_not_connected_prompts_connect() -> None:
    status = _status({}, None)
    assert status["resultLabel"] == (
        "Connect this device to sync your CFA progress across devices."
    )
    assert status["endpoint"] == "Not connected"


def test_result_label_connected_never_synced_names_account_and_endpoint() -> None:
    status = _status({"syncUser": "learner@ankiweb"}, None)
    label = status["resultLabel"]
    assert "learner@ankiweb" in label
    assert "AnkiWeb" in label
    assert "Sync now" in label
    assert status["endpoint"] == "AnkiWeb"


def test_result_label_synced_with_changes_says_synced_as_account() -> None:
    status = _status(
        {
            "syncUser": "learner@ankiweb",
            cc.CFA_LAST_SYNC_AT_KEY: "2026-07-05T14:32:00Z",
            cc.CFA_LAST_SYNC_CHANGED_KEY: True,
        },
        None,
    )
    assert status["resultLabel"] == "Synced as learner@ankiweb (AnkiWeb)."


def test_result_label_noop_sync_says_already_up_to_date() -> None:
    status = _status(
        {
            "syncUser": "learner@ankiweb",
            cc.CFA_LAST_SYNC_AT_KEY: "2026-07-05T14:32:00Z",
            cc.CFA_LAST_SYNC_CHANGED_KEY: False,
        },
        None,
    )
    assert status["resultLabel"] == "Already up to date as learner@ankiweb (AnkiWeb)."


def test_result_label_names_custom_server_endpoint() -> None:
    status = _status(
        {
            "syncUser": "learner@self",
            cc.CFA_LAST_SYNC_AT_KEY: "2026-07-05T14:32:00Z",
            cc.CFA_LAST_SYNC_CHANGED_KEY: True,
        },
        "https://sync.example.com/",
    )
    # Never leaks a raw URL — the endpoint reads as a human label.
    assert status["resultLabel"] == "Synced as learner@self (Custom server)."
    assert "http" not in status["resultLabel"]


def test_mark_sync_finished_flags_noop_vs_change() -> None:
    # A loaded profile always carries at least the account key; the empty-dict
    # fallback (no profile) is deliberately skipped by mark_sync_finished.
    profile: dict = {"syncUser": "learner@ankiweb"}
    col = SimpleNamespace(mod=111)
    mw = SimpleNamespace(pm=SimpleNamespace(profile=profile), col=col)

    # First recorded sync: no baseline mod yet, so count it as a change.
    cc.mark_sync_finished(mw)
    assert profile[cc.CFA_LAST_SYNC_CHANGED_KEY] is True
    assert profile[cc.CFA_LAST_SYNC_MOD_KEY] == 111
    assert profile[cc.CFA_LAST_SYNC_AT_KEY]

    # Second sync, collection unchanged -> a genuine no-op.
    cc.mark_sync_finished(mw)
    assert profile[cc.CFA_LAST_SYNC_CHANGED_KEY] is False

    # A local change bumps col.mod -> the next sync moved data.
    col.mod = 222
    cc.mark_sync_finished(mw)
    assert profile[cc.CFA_LAST_SYNC_CHANGED_KEY] is True
    assert profile[cc.CFA_LAST_SYNC_MOD_KEY] == 222


def test_mark_sync_finished_without_collection_does_not_claim_noop() -> None:
    profile: dict = {"syncUser": "learner@ankiweb"}
    mw = SimpleNamespace(pm=SimpleNamespace(profile=profile), col=None)
    cc.mark_sync_finished(mw)
    # Can't read col.mod -> never fabricate an "up to date" claim.
    assert profile[cc.CFA_LAST_SYNC_CHANGED_KEY] is True
    assert profile[cc.CFA_LAST_SYNC_AT_KEY]


# --- fresh-account-conflict + full-download reload ---------------------------


def test_trigger_cfa_sync_heals_then_delegates_to_standard_anki_sync(
    monkeypatch,
) -> None:
    # The fresh-account conflict dialog is Anki's own (sync_collection ->
    # full_sync). The CFA wrapper must NOT bypass it: it heals the endpoint and
    # then calls the stock on_sync_button_clicked, preserving that flow.
    order: list[str] = []
    monkeypatch.setattr(
        cc, "heal_stale_local_sync_url", lambda mw: order.append("heal")
    )

    mw = SimpleNamespace(
        pm=SimpleNamespace(sync_auth=lambda: object()),
        col=object(),
        on_sync_button_clicked=lambda: order.append("stock-sync"),
    )
    cc.trigger_cfa_sync(mw)  # type: ignore[arg-type]
    assert order == ["heal", "stock-sync"]


def test_connect_cfa_sync_heals_then_delegates_to_standard_anki_sync(
    monkeypatch,
) -> None:
    order: list[str] = []
    monkeypatch.setattr(
        cc, "heal_stale_local_sync_url", lambda mw: order.append("heal")
    )
    mw = SimpleNamespace(
        col=object(), on_sync_button_clicked=lambda: order.append("sync")
    )
    cc.connect_cfa_sync(mw)  # type: ignore[arg-type]
    assert order == ["heal", "sync"]


def test_standard_download_vs_upload_conflict_dialog_is_preserved() -> None:
    # Documents that CFA rides Anki's stock first-sync conflict flow: the
    # download-vs-upload dialog and the full-download confirmation still exist,
    # and the CFA wrapper reaches them via on_sync_button_clicked (never a
    # custom bypass).
    sync_src = (_REPO / "qt" / "aqt" / "sync.py").read_text(encoding="utf-8")
    for token in (
        "def full_sync",
        "sync_upload_to_ankiweb",
        "sync_download_from_ankiweb",
        "confirm_full_download",
        "confirm_full_upload",
    ):
        assert token in sync_src, f"stock sync conflict flow missing: {token}"

    cfa_src = (_REPO / "qt" / "aqt" / "cfa_sync_connect.py").read_text(encoding="utf-8")
    assert cfa_src.count("mw.on_sync_button_clicked()") >= 2


def test_sync_did_finish_reloads_open_cfa_screen(monkeypatch) -> None:
    # After ANY sync completion — including a FULL DOWNLOAD, whose on_done fires
    # gui_hooks.sync_did_finish() once the collection is reopened — the open CFA
    # screen reloads so a freshly-downloaded (e.g. new empty) account shows its
    # real state instead of stale data.
    import aqt.gui_hooks as gh

    fake = _fake_hook()
    monkeypatch.setattr(gh, "sync_did_finish", fake)
    monkeypatch.setattr(cc, "_SYNC_TRACKING_REGISTERED", False)

    loaded: list[str] = []

    mw = SimpleNamespace(
        state="cfaHome",
        web=SimpleNamespace(load_sveltekit_page=lambda page: loaded.append(page)),
        toolbar=SimpleNamespace(draw=lambda: None),
        pm=SimpleNamespace(profile={"syncUser": "learner@ankiweb"}),
        col=None,
    )
    cc.register_sync_status_tracking(mw)  # type: ignore[arg-type]
    assert len(fake.callbacks) == 1  # type: ignore[attr-defined]

    fake.callbacks[0]()  # type: ignore[attr-defined]  # simulate sync_did_finish
    assert loaded == ["cfa-home"]
    # And the finish timestamp was recorded for the status card.
    assert mw.pm.profile[cc.CFA_LAST_SYNC_AT_KEY]
