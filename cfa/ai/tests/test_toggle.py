# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Unit tests for the in-app AI toggle (col.conf keys).

The effective gate is ``key_present AND master AND per-feature``; all three
must hold. Toggles default ON (AI-first), so with a key present AI is on out of
the box; without a key the gate still forces off. These tests exercise every
combination with a fake collection (no network, no real key).
"""

from __future__ import annotations

import pytest

from cfa.ai import llm_client
from cfa.ai.llm_client import (
    CONF_AI_GRADING,
    CONF_AI_MASTER,
    CONF_AI_TABFILL,
    ai_feature_enabled,
    ai_toggle_state,
)


class FakeCol:
    """Duck-typed stand-in for anki.Collection: only get_config is used."""

    def __init__(self, conf: dict):
        self._conf = conf

    def get_config(self, key, default=None):
        return self._conf.get(key, default)


@pytest.fixture
def with_key(monkeypatch):
    """Pretend a key is configured, without touching the environment/.env."""
    monkeypatch.setattr(llm_client, "_get_api_key", lambda: "sk-test")


def test_defaults_on_with_key(with_key):
    # Fresh collection: no toggle keys set -> AI ON by default (AI-first), since
    # a key is present. Without a key it still gates off (see test_no_key_forces_off).
    col = FakeCol({})
    assert ai_feature_enabled("grading", col=col) is True
    assert ai_feature_enabled("tabfill", col=col) is True


def test_master_gates_all(with_key):
    # Feature switches on, but master explicitly OFF -> still OFF.
    col = FakeCol(
        {CONF_AI_MASTER: False, CONF_AI_GRADING: True, CONF_AI_TABFILL: True}
    )
    assert ai_feature_enabled("grading", col=col) is False
    assert ai_feature_enabled("tabfill", col=col) is False


def test_per_feature_independent(with_key):
    # master on, grading on, tabfill explicitly OFF.
    col = FakeCol(
        {CONF_AI_MASTER: True, CONF_AI_GRADING: True, CONF_AI_TABFILL: False}
    )
    assert ai_feature_enabled("grading", col=col) is True
    assert ai_feature_enabled("tabfill", col=col) is False


def test_all_on(with_key):
    col = FakeCol(
        {CONF_AI_MASTER: True, CONF_AI_GRADING: True, CONF_AI_TABFILL: True}
    )
    assert ai_feature_enabled("grading", col=col) is True
    assert ai_feature_enabled("tabfill", col=col) is True


def test_no_key_forces_off(monkeypatch):
    # No key: even with every switch on, the gate is OFF.
    monkeypatch.setattr(llm_client, "_get_api_key", lambda: None)
    col = FakeCol(
        {CONF_AI_MASTER: True, CONF_AI_GRADING: True, CONF_AI_TABFILL: True}
    )
    assert ai_feature_enabled("grading", col=col) is False
    state = ai_toggle_state(col=col)
    assert state["key_present"] is False
    assert state["grading_on"] is False
    # The stored switch values are still reported for the UI.
    assert state["master"] is True and state["grading"] is True


def test_conf_mapping_accepted(with_key):
    # A plain mapping (e.g. col.all_config()) works instead of a col.
    conf = {CONF_AI_MASTER: True, CONF_AI_TABFILL: True, CONF_AI_GRADING: False}
    assert ai_feature_enabled("tabfill", conf=conf) is True
    assert ai_feature_enabled("grading", conf=conf) is False


def test_unknown_feature_raises(with_key):
    with pytest.raises(ValueError):
        ai_feature_enabled("nonsense", col=FakeCol({}))
