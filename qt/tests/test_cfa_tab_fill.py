# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F3 tests — AI tab-to-fill card backs.

The real logic (:func:`draft_back`, :func:`fill_note_back`) is exercised with a
plain note-like stub and an injected completion function, so no live editor,
webview, or network is needed. The AI-off path uses the real default client
(no ``OPENAI_API_KEY`` in CI) and must refuse gracefully without mutating the
note — the deterministic-safe contract.
"""

import pytest

pytest.importorskip("aqt")

from aqt.cfa_tab_fill import (  # noqa: E402
    AI_TAG,
    build_messages,
    draft_back,
    fill_note_back,
    find_field_indices,
    register,
)


class FakeNote:
    """Minimal stand-in for anki.notes.Note used by the pure functions."""

    def __init__(self, field_names, fields, tags=None, notetype="Basic"):
        self._names = list(field_names)
        self.fields = list(fields)
        self.tags = list(tags or [])
        self._notetype = notetype

    def keys(self):
        return list(self._names)

    def note_type(self):
        return {"name": self._notetype}


def _ok_complete(text="Standard III(B): allocate trades fairly across clients."):
    calls = {}

    def complete(system, user, **kw):
        calls["system"] = system
        calls["user"] = user
        calls["kw"] = kw
        return {"ok": True, "text": text, "model": "gpt-4o-mini", "error": None}

    complete.calls = calls  # type: ignore[attr-defined]
    return complete


def _off_complete(error="no_api_key"):
    def complete(system, user, **kw):
        return {"ok": False, "text": "", "model": "gpt-4o-mini", "error": error}

    return complete


# --- draft_back --------------------------------------------------------------


def test_draft_back_ok_with_mocked_client():
    res = draft_back(
        "What does Standard III(B) require?", "Basic", complete_fn=_ok_complete()
    )
    assert res["ok"] is True
    assert "Standard III(B)" in res["text"]
    assert res["model"] == "gpt-4o-mini"


def test_draft_back_empty_front_refused():
    res = draft_back("   ", complete_fn=_ok_complete())
    assert res["ok"] is False and res["error"] == "empty_front"


def test_draft_back_ai_off_falls_back():
    res = draft_back("Front content", complete_fn=_off_complete())
    assert res["ok"] is False and res["error"] == "no_api_key" and res["text"] == ""


def test_build_messages_carries_front_and_notetype():
    system, user = build_messages("Define duration", "CFA Cloze")
    assert "flashcard" in system.lower()
    assert "Define duration" in user and "CFA Cloze" in user


# --- fill_note_back ----------------------------------------------------------


def test_fill_note_back_fills_and_tags_provenance():
    note = FakeNote(["Front", "Back"], ["What is the MPS proxy?", ""])
    res = fill_note_back(
        note, complete_fn=_ok_complete("~65% minimum passing standard.")
    )
    assert res["ok"] is True and res["status"] == "filled"
    # back field written, front untouched
    assert note.fields[1] == "~65% minimum passing standard."
    assert note.fields[0] == "What is the MPS proxy?"
    # provenance tag added (the whole point of F3)
    assert AI_TAG in note.tags


def test_fill_note_back_tagging_is_idempotent():
    note = FakeNote(["Front", "Back"], ["Q", ""], tags=[AI_TAG])
    fill_note_back(note, complete_fn=_ok_complete())
    assert note.tags.count(AI_TAG) == 1


def test_fill_note_back_refuses_empty_front():
    note = FakeNote(["Front", "Back"], ["", ""])
    res = fill_note_back(note, complete_fn=_ok_complete())
    assert res["status"] == "empty_front"
    assert AI_TAG not in note.tags and note.fields[1] == ""


def test_fill_note_back_never_overwrites_without_confirm():
    note = FakeNote(["Front", "Back"], ["Q", "existing answer"])
    res = fill_note_back(
        note, complete_fn=_ok_complete(), confirm_overwrite=lambda: False
    )
    assert res["status"] == "cancelled"
    assert note.fields[1] == "existing answer"  # untouched
    assert AI_TAG not in note.tags


def test_fill_note_back_overwrites_when_confirmed():
    note = FakeNote(["Front", "Back"], ["Q", "old"])
    res = fill_note_back(
        note, complete_fn=_ok_complete("new answer"), confirm_overwrite=lambda: True
    )
    assert res["ok"] is True and res["overwrote"] is True
    assert note.fields[1] == "new answer" and AI_TAG in note.tags


def test_fill_note_back_ai_off_leaves_note_untouched():
    """With the REAL default client and no key, the note must be unchanged."""
    note = FakeNote(["Front", "Back"], ["A real front", ""])
    res = fill_note_back(note)  # no complete_fn -> real llm_client, AI off in CI
    assert res["ok"] is False and res["status"] == "ai_unavailable"
    assert note.fields[1] == "" and AI_TAG not in note.tags


def test_fill_note_back_single_field_notetype():
    note = FakeNote(["Text"], ["only field"], notetype="Cloze")
    res = fill_note_back(note, complete_fn=_ok_complete())
    assert res["status"] == "single_field"


def test_fill_note_back_strips_html_from_front():
    note = FakeNote(["Front", "Back"], ["<b>Bond&nbsp;convexity</b>", ""])
    comp = _ok_complete()
    fill_note_back(note, complete_fn=comp)
    # the front reaching the model is plain text, not markup
    assert "<b>" not in comp.calls["user"]
    assert "Bond convexity" in comp.calls["user"]


# --- field location ----------------------------------------------------------


def test_find_field_indices_by_name():
    note = FakeNote(["Question", "Answer"], ["q", "a"])
    assert find_field_indices(note) == (0, 1)


def test_find_field_indices_reversed_names():
    note = FakeNote(["Answer", "Question"], ["a", "q"])
    front, back = find_field_indices(note)
    # front should map to the Question field, back to the Answer field
    assert front == 1 and back == 0


def test_find_field_indices_positional_fallback():
    note = FakeNote(["FieldA", "FieldB"], ["x", "y"])
    assert find_field_indices(note) == (0, 1)


# --- editor wiring -----------------------------------------------------------


def test_button_disabled_when_ai_off(monkeypatch):
    import aqt.cfa_tab_fill as tf

    monkeypatch.setattr(tf, "_ai_enabled", lambda: False)
    buttons: list = []
    tf._on_init_buttons(buttons, object())
    assert len(buttons) == 1
    assert "disabled" in buttons[0] and tf._BUTTON_LABEL in buttons[0]


def test_button_enabled_uses_addButton(monkeypatch):
    import aqt.cfa_tab_fill as tf

    monkeypatch.setattr(tf, "_ai_enabled", lambda: True)

    seen = {}

    class FakeEditor:
        def addButton(self, **kw):
            seen.update(kw)
            return "<button>AI Back</button>"

    buttons: list = []
    tf._on_init_buttons(buttons, FakeEditor())
    assert seen["cmd"] == tf.FILL_CMD
    assert seen["keys"] == tf.FILL_SHORTCUT
    assert seen["func"] is tf._fill_back_action
    assert buttons == ["<button>AI Back</button>"]


def test_register_is_idempotent():
    from aqt import gui_hooks

    register()
    n1 = len(gui_hooks.editor_did_init_buttons._hooks)
    register()
    n2 = len(gui_hooks.editor_did_init_buttons._hooks)
    assert n1 == n2
