# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F3 tests — AI tab-to-fill card backs.

The real logic (:func:`draft_back`, :func:`fill_note_back`) is exercised with a
plain note-like stub and an injected completion function, so no live editor,
webview, or network is needed. The AI-off path uses the real default client
(no ``OPENAI_API_KEY`` in CI) and must refuse gracefully without mutating the
note — the deterministic-safe contract.
"""

import re

import pytest

pytest.importorskip("aqt")

from aqt.cfa_tab_fill import (  # noqa: E402
    AI_TAG,
    build_messages,
    draft_back,
    draft_field,
    fill_note,
    fill_note_back,
    find_field_indices,
    register,
)


def _button_tag(html: str) -> str:
    """Return the opening ``<button ...>`` tag from a button HTML fragment."""
    m = re.search(r"<button\b[^>]*>", html)
    assert m, f"no <button> found in {html!r}"
    return m.group(0)


def _has_class(tag: str, cls: str) -> bool:
    m = re.search(r'class="([^"]*)"', tag)
    return bool(m) and cls in m.group(1).split()


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
    """With the REAL default client and AI off, the note must be unchanged.

    Tolerant of a working ``OPENAI_API_KEY`` in the local .env (iter 2): the
    AI-off *contract* is only asserted when the client is actually off; when a
    key is present the real call may legitimately fill and tag the note.
    """
    import aqt.cfa_tab_fill as tf

    note = FakeNote(["Front", "Back"], ["A real front", ""])
    res = fill_note_back(note)  # no complete_fn -> real llm_client
    if tf._ai_enabled():
        # Key present: either it drafted (filled + tagged) or failed gracefully.
        if res["ok"]:
            assert note.fields[1] != "" and AI_TAG in note.tags
        else:
            assert note.fields[1] == "" and AI_TAG not in note.tags
    else:
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


# --- AI-off button: visibly disabled + working tooltip (MEDIUM #9) -----------


def test_button_html_disabled_carries_perm_class():
    """AI-off button must carry ``perm`` so it stays visibly disabled.

    Anki's editor JS re-enables every ``button.linkb:not(.perm)`` when a field
    gains focus, so without ``perm`` the ``disabled`` attribute is stripped and
    the button no longer looks or behaves disabled.
    """
    import aqt.cfa_tab_fill as tf

    tag = _button_tag(tf._button_html(enabled=False))
    assert "disabled" in tag, tag
    assert _has_class(tag, "linkb"), tag
    assert _has_class(tag, "perm"), tag


def test_button_html_disabled_tooltip_lives_on_wrapper_span():
    """A ``title`` on a disabled ``<button>`` never tooltips; a wrapper span does.

    Browsers suppress pointer/hover events (and thus the native title tooltip)
    on disabled controls, so the explanatory hover text must ride on an enabled
    ``<span>`` wrapping the disabled button.
    """
    import aqt.cfa_tab_fill as tf

    html = tf._button_html(enabled=False).strip()
    assert html.startswith("<span"), html
    assert html.endswith("</span>"), html
    span_open = re.search(r"<span\b[^>]*>", html).group(0)  # type: ignore[union-attr]
    assert "title=" in span_open, span_open
    assert "OPENAI_API_KEY" in span_open, span_open
    # the disabled button is nested inside that span
    assert "<button" in html and "disabled" in html


def test_button_html_enabled_is_plain_and_has_no_perm():
    import aqt.cfa_tab_fill as tf

    html = tf._button_html(enabled=True)
    tag = _button_tag(html)
    assert "disabled" not in tag, tag
    assert not _has_class(tag, "perm"), tag
    assert "<span" not in html, html
    assert tf._BUTTON_LABEL in html


def test_on_init_buttons_ai_off_is_disabled_with_perm_and_tooltip(monkeypatch):
    import aqt.cfa_tab_fill as tf

    monkeypatch.setattr(tf, "_ai_enabled", lambda: False)
    buttons: list = []
    tf._on_init_buttons(buttons, object())
    assert len(buttons) == 1
    html = buttons[0].strip()
    tag = _button_tag(html)
    assert "disabled" in tag and _has_class(tag, "perm"), tag
    assert html.startswith("<span") and "title=" in html
    assert "OPENAI_API_KEY" in html


def test_on_init_buttons_ai_on_is_enabled_without_perm(monkeypatch):
    import aqt.cfa_tab_fill as tf

    monkeypatch.setattr(tf, "_ai_enabled", lambda: True)

    class FakeEditor:
        def addButton(self, **kw):
            # mirror aqt.editor._addButton's enabled (non-perm) markup
            return (
                '<button class="anki-addon-button linkb" type="button">AI Back</button>'
            )

    buttons: list = []
    tf._on_init_buttons(buttons, FakeEditor())
    assert len(buttons) == 1
    assert "perm" not in buttons[0]
    assert "disabled" not in buttons[0]


def test_register_is_idempotent():
    from aqt import gui_hooks

    register()
    n1 = len(gui_hooks.editor_did_init_buttons._hooks)
    register()
    n2 = len(gui_hooks.editor_did_init_buttons._hooks)
    assert n1 == n2


# --- bidirectional fill (front<->back) --------------------------------------


def _basic(front, back):
    return FakeNote(["Front", "Back"], [front, back])


def test_fill_note_front_to_back():
    note = _basic("What is the MPS proxy?", "")
    res = fill_note(note, complete_fn=_ok_complete("~65% minimum passing standard."))
    assert res["ok"] and res["status"] == "filled" and res["target"] == "back"
    assert note.fields[1] == "~65% minimum passing standard."
    assert note.fields[0] == "What is the MPS proxy?"  # source untouched
    assert AI_TAG in note.tags


def test_fill_note_back_to_front():
    note = _basic("", "Modified duration estimates price change per 1% yield move.")
    res = fill_note(
        note, complete_fn=_ok_complete("What does modified duration estimate?")
    )
    assert res["ok"] and res["status"] == "filled" and res["target"] == "front"
    assert note.fields[0] == "What does modified duration estimate?"
    assert note.fields[1].startswith("Modified duration")  # source untouched
    assert AI_TAG in note.tags


def test_fill_note_nothing_when_both_filled():
    note = _basic("Q", "A")
    res = fill_note(note, complete_fn=_ok_complete())
    assert res["status"] == "nothing_to_fill"
    assert note.fields == ["Q", "A"] and AI_TAG not in note.tags


def test_fill_note_nothing_when_both_empty():
    res = fill_note(_basic("  ", ""), complete_fn=_ok_complete())
    assert res["status"] == "nothing_to_fill"


def test_draft_field_both_directions():
    assert draft_field("Q", "back", complete_fn=_ok_complete("A"))["ok"] is True
    r = draft_field("A", "front", complete_fn=_ok_complete("Q?"))
    assert r["ok"] is True and r["target"] == "front"


# --- Tab-key trigger --------------------------------------------------------


def test_tab_js_fires_fill_without_preventing_default():
    import aqt.cfa_tab_fill as tf

    js = tf._TAB_JS
    assert "'Tab'" in js
    assert tf.FILL_CMD in js
    assert "pycmd" in js
    assert "preventDefault" not in js  # Tab must still navigate fields normally


def test_on_editor_init_injects_tab_js():
    import aqt.cfa_tab_fill as tf

    class FakeWeb:
        def __init__(self):
            self.evald: list = []

        def eval(self, js):
            self.evald.append(js)

    class FakeEditor:
        def __init__(self):
            self.web = FakeWeb()

    ed = FakeEditor()
    tf._on_editor_init(ed)
    assert any(tf.FILL_CMD in j for j in ed.web.evald)


def test_fill_action_silent_and_no_save_when_ai_off(monkeypatch):
    import aqt.cfa_tab_fill as tf

    monkeypatch.setattr(tf, "_ai_enabled", lambda: False)
    saved: list = []

    class FakeEditor:
        note = FakeNote(["Front", "Back"], ["Q", ""])
        widget = None

        def call_after_note_saved(self, cb, keepFocus=False):
            saved.append(True)
            cb()

    tf._fill_back_action(FakeEditor())
    assert saved == []  # AI off -> returns before saving; no fill attempted


def test_register_wires_editor_did_init():
    import aqt.cfa_tab_fill as tf
    from aqt import gui_hooks

    tf._REGISTERED = False
    tf.register()
    assert tf._on_editor_init in gui_hooks.editor_did_init._hooks


# --- contextual Tab affordance (D-P4-6) -------------------------------------


def test_should_invite_only_when_exactly_one_side_filled():
    from aqt.cfa_tab_fill import should_invite

    # AI on, front filled + back empty -> invite on the back (where text lands).
    assert should_invite("<b>What is Std III(B)?</b>", "", True) == "back"
    # AI on, back filled + front empty -> invite on the front.
    assert should_invite("", "Allocate trades fairly.", True) == "front"
    # Both filled / both empty -> no invite (matches fill_note's rule).
    assert should_invite("Q", "A", True) is None
    assert should_invite("", "", True) is None
    assert should_invite("&nbsp; <br>", "A", True) == "front"  # blank-ish front


def test_should_invite_never_when_ai_off():
    from aqt.cfa_tab_fill import should_invite

    assert should_invite("Q", "", False) is None
    assert should_invite("", "A", False) is None


def test_hint_js_is_contextual_and_reads_live_empty_class():
    """The affordance must key off the editor's own live `.rich-text-editable
    .empty` class (no shadow traversal) and render the Tab invitation."""
    import aqt.cfa_tab_fill as tf

    js = tf._HINT_JS
    assert ".rich-text-editable" in js
    assert "'empty'" in js
    assert "field-container[data-index" in js
    assert "Press <kbd>Tab</kbd> to generate this with AI" in js
    assert "MutationObserver" in js  # tracks typing live
    assert "window.__cfaTabFill" in js
    assert "aria-hidden" in js  # button/tooltip already announce; avoid double-read


def test_hint_style_stays_on_cfa_palette_no_monospace():
    import aqt.cfa_tab_fill as tf

    js = tf._HINT_JS
    assert "#14b8b1" in js  # turquoise CFA accent on the AI sparkle
    assert "font:inherit" in js  # kbd cap uses body font, never monospace


def test_on_editor_init_injects_both_tab_and_hint_js():
    import aqt.cfa_tab_fill as tf

    class FakeWeb:
        def __init__(self):
            self.evald: list = []

        def eval(self, js):
            self.evald.append(js)

    class FakeEditor:
        def __init__(self):
            self.web = FakeWeb()

    ed = FakeEditor()
    tf._on_editor_init(ed)
    assert any("__cfaTabFill" in j and "configure" in j for j in ed.web.evald)


def test_configure_hint_sends_indices_and_ai_state():
    import aqt.cfa_tab_fill as tf

    class FakeWeb:
        def __init__(self):
            self.evald: list = []

        def eval(self, js):
            self.evald.append(js)

    class FakeEditor:
        def __init__(self, note):
            self.note = note
            self.web = FakeWeb()

    # AI on + a normal 2-field note -> configure with the located indices.
    tf_ai_on = tf._ai_enabled
    try:
        tf._ai_enabled = lambda: True  # type: ignore[assignment]
        ed = FakeEditor(FakeNote(["Front", "Back"], ["Q", ""]))
        tf._configure_hint(ed)
        cfg = [j for j in ed.web.evald if "configure(" in j]
        assert cfg and "configure(0,1,true)" in cfg[0]

        # AI off -> still configures, but disabled so the hint never shows.
        tf._ai_enabled = lambda: False  # type: ignore[assignment]
        ed2 = FakeEditor(FakeNote(["Front", "Back"], ["Q", ""]))
        tf._configure_hint(ed2)
        assert any("configure(0,1,false)" in j for j in ed2.web.evald)
    finally:
        tf._ai_enabled = tf_ai_on  # type: ignore[assignment]


def test_configure_hint_single_field_note_disables_invite():
    import aqt.cfa_tab_fill as tf

    class FakeWeb:
        def __init__(self):
            self.evald: list = []

        def eval(self, js):
            self.evald.append(js)

    class FakeEditor:
        def __init__(self, note):
            self.note = note
            self.web = FakeWeb()

    tf_ai_on = tf._ai_enabled
    try:
        tf._ai_enabled = lambda: True  # type: ignore[assignment]
        ed = FakeEditor(FakeNote(["Text"], [""]))
        tf._configure_hint(ed)
        # front_idx == back_idx for a 1-field note -> nulls + disabled.
        assert any("configure(null,null,false)" in j for j in ed.web.evald)
    finally:
        tf._ai_enabled = tf_ai_on  # type: ignore[assignment]


def test_register_wires_load_note_hook():
    import aqt.cfa_tab_fill as tf
    from aqt import gui_hooks

    tf._REGISTERED = False
    tf.register()
    assert tf._configure_hint in gui_hooks.editor_did_load_note._hooks
