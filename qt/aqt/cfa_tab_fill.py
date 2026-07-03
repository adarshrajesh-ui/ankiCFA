# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F3 — AI "tab-to-fill" card backs in the desktop editor.

When the front of a note has content and the back is empty, a visible editor
button (and the ``Ctrl+Alt+F`` shortcut) drafts the back with the LLM, inserts
it into the back field, and tags the note ``ai-generated`` so the provenance is
always recorded.

Design rules (from the project objective):

* **AI OFF must be safe.** With no ``OPENAI_API_KEY`` the button renders
  *disabled* with an explanatory tooltip and never calls out. Availability is
  decided by :func:`cfa.ai.llm_client.ai_enabled` (key presence only, no call).
* **Never destroy work.** A non-empty back is only overwritten after the user
  confirms; an empty front is refused with a tooltip.
* **Additive + testable.** All the real logic lives in pure functions
  (:func:`draft_back`, :func:`fill_note_back`) that take an injected completion
  function and a plain note-like object, so they unit-test without a live
  editor, webview, or network. The editor wiring is a thin adapter.

Shortcut note (documented tradeoff): the objective calls this "tab-to-fill",
but binding the raw ``Tab`` key in the rich-text editor would hijack field
navigation — a real regression. We therefore bind a dedicated ``Ctrl+Alt+F``
shortcut plus the always-visible button, and leave ``Tab`` doing its normal
job. Same one-keystroke "fill the back" intent, no lost navigation.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

# --- provenance + configuration ---------------------------------------------

AI_TAG = "ai-generated"
FILL_SHORTCUT = "Ctrl+Alt+F"
FILL_CMD = "cfaTabFill"
_BUTTON_LABEL = "AI Back"

# Field-name heuristics for locating the "front" (prompt) and "back" (answer)
# fields regardless of note type. Matching is case-insensitive; the first hit
# wins, and we fall back to positional indices (0 -> front, 1 -> back).
_FRONT_NAMES = ("front", "question", "text", "prompt", "term")
_BACK_NAMES = ("back", "answer", "extra", "explanation", "definition", "notes")

CompleteFn = Callable[..., dict]
ConfirmFn = Callable[[], bool]


# --- HTML helpers ------------------------------------------------------------


def _strip_html(html: str) -> str:
    """Best-effort plain-text of a field for the prompt (no anki dependency)."""
    # Drop tags, collapse whitespace, and decode the handful of entities Anki
    # fields commonly carry. Kept dependency-free so the pure functions import
    # cleanly under a bare pytest.
    text = re.sub(r"<[^>]+>", " ", html or "")
    for ent, ch in (
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
    ):
        text = text.replace(ent, ch)
    return re.sub(r"\s+", " ", text).strip()


def _is_blank(html: str) -> bool:
    return _strip_html(html) == ""


# --- field location ----------------------------------------------------------


def _field_names(note: Any) -> list[str]:
    try:
        names = list(note.keys())
        if names:
            return names
    except Exception:  # pragma: no cover - defensive
        pass
    return [""] * len(getattr(note, "fields", []) or [])


def find_field_indices(note: Any) -> tuple[int, int]:
    """Return ``(front_idx, back_idx)`` for a note-like object.

    Prefers fields whose names look like a prompt / answer; otherwise falls
    back to position 0 for the front and the next distinct field for the back.
    """
    names = [n.lower() for n in _field_names(note)]
    n = len(getattr(note, "fields", []) or names)
    if n < 2:
        # A single-field note has no separate back to fill.
        return (0, 0 if n <= 1 else 1)

    front_idx: Optional[int] = None
    back_idx: Optional[int] = None
    for i, name in enumerate(names):
        if front_idx is None and any(k in name for k in _FRONT_NAMES):
            front_idx = i
        elif back_idx is None and any(k in name for k in _BACK_NAMES):
            back_idx = i

    if front_idx is None:
        front_idx = 0
    if back_idx is None or back_idx == front_idx:
        back_idx = 1 if front_idx != 1 else 0
    return (front_idx, back_idx)


# --- prompt construction -----------------------------------------------------


def build_messages(front_text: str, notetype_name: str = "") -> tuple[str, str]:
    """Build the (system, user) prompt for drafting a card back."""
    system = (
        "You are a CFA charterholder and exam tutor writing the answer side of a "
        "study flashcard. Given the front of the card, write a concise, exam-accurate "
        "back that a Level II candidate can learn from. Rules: answer the front "
        "directly; be correct and specific (name the standard, formula, or definition "
        "where relevant); prefer 1-4 short sentences or a tight bullet list; no "
        "preamble, no restating the question, no markdown headers. Return only the "
        "answer text."
    )
    ctx = f" (note type: {notetype_name})" if notetype_name else ""
    user = f"Front of card{ctx}:\n{front_text}\n\nWrite the back of the card."
    return system, user


# --- pure drafting + application ---------------------------------------------


def draft_back(
    front_text: str,
    notetype_name: str = "",
    *,
    complete_fn: Optional[CompleteFn] = None,
    max_tokens: int = 400,
) -> dict:
    """Draft a card back from the front text. Never raises.

    Returns ``{ok, text, error, model}``. ``ok`` is False (with ``text``
    empty) whenever AI is off or the call fails, so callers stay AI-off safe.
    ``complete_fn`` is injectable for tests; it defaults to the shared client.
    """
    front_text = (front_text or "").strip()
    if not front_text:
        return {"ok": False, "text": "", "error": "empty_front", "model": None}

    if complete_fn is None:
        from cfa.ai.llm_client import complete as complete_fn  # type: ignore

    system, user = build_messages(front_text, notetype_name)
    try:
        res = complete_fn(
            system,
            user,
            max_tokens=max_tokens,
            temperature=0.2,
            purpose="tab_fill_back",
        )
    except Exception as exc:  # pragma: no cover - client is no-raise; belt+braces
        return {
            "ok": False,
            "text": "",
            "error": f"client_error:{type(exc).__name__}",
            "model": None,
        }

    if not isinstance(res, dict) or not res.get("ok"):
        return {
            "ok": False,
            "text": "",
            "error": (res or {}).get("error", "ai_unavailable"),
            "model": (res or {}).get("model"),
        }
    text = (res.get("text") or "").strip()
    if not text:
        return {
            "ok": False,
            "text": "",
            "error": "empty_completion",
            "model": res.get("model"),
        }
    return {"ok": True, "text": text, "error": None, "model": res.get("model")}


def _tag_note(note: Any) -> None:
    tags = getattr(note, "tags", None)
    if isinstance(tags, list) and AI_TAG not in tags:
        tags.append(AI_TAG)


def fill_note_back(
    note: Any,
    *,
    complete_fn: Optional[CompleteFn] = None,
    confirm_overwrite: Optional[ConfirmFn] = None,
    front_idx: Optional[int] = None,
    back_idx: Optional[int] = None,
) -> dict:
    """Fill a note's back field from its front. Pure w.r.t. UI. Never raises.

    Returns a result dict with a ``status`` in
    ``{"filled", "no_note", "single_field", "empty_front", "cancelled",
    "ai_unavailable"}``. On success the note's back field is set and the note
    is tagged :data:`AI_TAG` (provenance). A non-empty back is only touched
    when ``confirm_overwrite()`` returns True.
    """
    fields = getattr(note, "fields", None)
    if not fields:
        return {"ok": False, "status": "no_note", "text": "", "error": "no_note"}
    if front_idx is None or back_idx is None:
        fi, bi = find_field_indices(note)
        front_idx = fi if front_idx is None else front_idx
        back_idx = bi if back_idx is None else back_idx
    if len(fields) < 2 or front_idx == back_idx:
        return {
            "ok": False,
            "status": "single_field",
            "text": "",
            "error": "single_field",
        }

    if _is_blank(fields[front_idx]):
        return {
            "ok": False,
            "status": "empty_front",
            "text": "",
            "error": "empty_front",
        }

    overwrote = False
    if not _is_blank(fields[back_idx]):
        if confirm_overwrite is None or not confirm_overwrite():
            return {
                "ok": False,
                "status": "cancelled",
                "text": "",
                "error": "cancelled",
            }
        overwrote = True

    front_text = _strip_html(fields[front_idx])
    notetype_name = ""
    try:
        notetype_name = note.note_type()["name"]  # type: ignore[index]
    except Exception:
        pass

    drafted = draft_back(front_text, notetype_name, complete_fn=complete_fn)
    if not drafted["ok"]:
        return {
            "ok": False,
            "status": "ai_unavailable",
            "text": "",
            "error": drafted["error"],
        }

    fields[back_idx] = drafted["text"]
    _tag_note(note)
    return {
        "ok": True,
        "status": "filled",
        "text": drafted["text"],
        "error": None,
        "back_idx": back_idx,
        "overwrote": overwrote,
        "model": drafted["model"],
    }


# --- editor wiring (thin adapter) -------------------------------------------


def _ai_enabled() -> bool:
    try:
        from cfa.ai.llm_client import ai_enabled

        return bool(ai_enabled())
    except Exception:  # pragma: no cover - defensive
        return False


def _fill_back_action(editor: Any) -> None:
    """Editor button/shortcut handler. Runs after the note is saved."""
    from aqt.utils import askUser, tooltip

    note = getattr(editor, "note", None)
    if note is None:
        return
    if not _ai_enabled():
        tooltip(
            "AI is off — set OPENAI_API_KEY to enable AI Back.", parent=editor.widget
        )
        return

    def _confirm() -> bool:
        return askUser(
            "This card's back is not empty. Replace it with an AI-drafted back?",
            parent=editor.widget,
            title="AI Back",
        )

    result = fill_note_back(note, confirm_overwrite=_confirm)
    status = result["status"]
    if status == "filled":
        # Reflect the new field + provenance tag in the web view.
        editor.loadNote()
        tooltip("Drafted the back with AI · tagged ai-generated", parent=editor.widget)
    elif status == "empty_front":
        tooltip("Add some front content first.", parent=editor.widget)
    elif status == "single_field":
        tooltip(
            "This note type has no separate back field to fill.", parent=editor.widget
        )
    elif status == "cancelled":
        pass  # user declined the overwrite
    else:  # ai_unavailable / no_note
        tooltip("AI Back is unavailable right now — try again.", parent=editor.widget)


def _button_html(enabled: bool) -> str:
    """Disabled button HTML for AI-off; the enabled button comes from addButton."""
    tip = "AI is off — set OPENAI_API_KEY to enable"
    return (
        f'<button tabindex=-1 class="anki-addon-button linkb" type="button" '
        f'disabled title="{tip}" data-command="{FILL_CMD}Disabled">{_BUTTON_LABEL}</button>'
    )


def _on_init_buttons(buttons: list, editor: Any) -> None:
    """gui_hooks.editor_did_init_buttons handler: add the AI Back button."""
    if _ai_enabled():
        btn = editor.addButton(
            icon=None,
            cmd=FILL_CMD,
            func=_fill_back_action,
            tip=f"Draft the back with AI ({FILL_SHORTCUT})",
            label=_BUTTON_LABEL,
            keys=FILL_SHORTCUT,
        )
    else:
        btn = _button_html(enabled=False)
    buttons.append(btn)


_REGISTERED = False


def register() -> None:
    """Register the editor button + shortcut exactly once (idempotent)."""
    global _REGISTERED
    if _REGISTERED:
        return
    from aqt import gui_hooks

    gui_hooks.editor_did_init_buttons.append(_on_init_buttons)
    _REGISTERED = True


__all__ = [
    "AI_TAG",
    "FILL_SHORTCUT",
    "build_messages",
    "draft_back",
    "fill_note_back",
    "find_field_indices",
    "register",
]
