# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork: desktop UI surface for the honest memory score.

Adds a "CFA" menu with:

* "Exam Readiness…" — reports the per-topic FSRS retrievability as a range
  (never a bare number) and enforces the give-up rule ("not enough data").
* "Study Ethics Minimal-Pairs" — filters to the ``CFA::Ethics Pairs`` deck and
  opens the reviewer.
* "Study Ethics (One-Passage)" — seeds the ``CFA::Ethics Passages`` F1
  one-passage flagship deck on demand and enters review on it (a normal,
  non-filtered deck), so the flagship is reachable on desktop.
* "Study by Exam Priority" — builds the read-only exam-priority queue
  (``build_exam_queue``) and opens a filtered deck ordered by that priority.
* "Peak-on-Exam-Day (Deadline)…" — ranks the current deck's due AND new cards
  by predicted FSRS recall AT the exam date (``cfa.deadline_retention_with_new``,
  which wraps ``cfa_deadline``), weakest first — new cards count as recall 0.0 so
  a fresh all-new deck still ranks. The persisted exam date is self-healed if it
  is absurd/far-future.

No AI — pure spaced-repetition statistics throughout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from anki import cfa
from anki.decks import DEFAULT_DECK_ID, DeckId
from aqt.qt import (
    QDialog,
    QMenu,
    QVBoxLayout,
    qconnect,
)
from aqt.utils import showInfo, showWarning, tooltip
from aqt.webview import AnkiWebView, AnkiWebViewKind

if TYPE_CHECKING:
    from datetime import date

    from aqt.main import AnkiQt

# Deck names used by the CFA fork.
ETHICS_DECK_NAME = "CFA::Ethics Pairs"
ETHICS_PASSAGES_DECK_NAME = "CFA::Ethics Passages"
EXAM_PRIORITY_DECK_NAME = "CFA::Exam Priority"


def setup_menu(mw: AnkiQt) -> None:
    """Add a top-level CFA menu, consistent with the CFA Home dashboard CTAs.

    Single ethics entry (Minimal-Pairs, the flagship); the one-passage drill is
    retired from the menu. ``study_ethics_passages`` remains callable for
    compatibility, it is simply no longer surfaced here."""
    menu = QMenu("&CFA", mw)

    home = menu.addAction("CFA Home")
    qconnect(home.triggered, lambda: mw.moveToState("cfaHome"))

    readiness = menu.addAction("Exam Readiness…")
    qconnect(readiness.triggered, lambda: show_exam_readiness(mw))

    ethics = menu.addAction("Study Ethics Minimal-Pairs")
    qconnect(ethics.triggered, lambda: study_ethics_pairs(mw))

    priority = menu.addAction("Study by Exam Priority")
    qconnect(priority.triggered, lambda: study_by_exam_priority(mw))

    deadline = menu.addAction("Peak-on-Exam-Day (Deadline)…")
    qconnect(deadline.triggered, lambda: show_deadline(mw))

    # Keep a reference so the menu (and its slots) survive garbage collection.
    mw._cfa_menu = menu  # type: ignore[attr-defined]
    mw.form.menubar.addMenu(menu)

    # F2: register the semantic ethics-highlight grading bridge (pycmd). Safe
    # to call unconditionally — it falls back to the deterministic grade when
    # AI is off, and it never raises during registration.
    try:
        from aqt.cfa_ethics_ai import register as _register_ethics_ai

        _register_ethics_ai()
    except Exception:
        pass

    # F3: register the editor "AI Back" tab-to-fill button + shortcut. Safe to
    # call unconditionally — with AI off the button renders disabled with a
    # tooltip, and registration never raises.
    try:
        from aqt.cfa_tab_fill import register as _register_tab_fill

        _register_tab_fill()
    except Exception:
        pass


def show_exam_readiness(mw: AnkiQt) -> None:
    if not mw.col:
        return
    deck_id = mw.col.decks.get_current_id()
    ExamReadinessDialog(mw, deck_id).exec()


# =============================================================================
# Study actions (each launches a real study/reporting flow, never crashes)
# =============================================================================


def _study_filtered_deck(
    mw: AnkiQt,
    *,
    name: str,
    search: str,
    order: int,
    limit: int = 200,
    reschedule: bool = True,
) -> bool:
    """Create/refresh a filtered deck for ``search`` and move into the reviewer.

    Returns True if cards were gathered and the reviewer was entered; False (with
    a tooltip) when there is nothing to study. Read-through to the scheduler's
    filtered-deck backend — never mutates FSRS history beyond normal rescheduling.
    """
    from anki.decks import FilteredDeckConfig
    from anki.errors import FilteredDeckError

    col = mw.col
    if not col:
        return False

    # Reuse an existing same-named filtered deck instead of creating a fresh,
    # name-colliding one. On a repeat invocation the previous build still holds
    # its cards, and Anki will not gather cards that already live inside a
    # filtered deck — so a brand-new deck (deck_id=0) would gather 0 and
    # dead-end. Passing the existing deck's id makes add_or_update_filtered_deck
    # rebuild it in place: it first returns the cards home, then re-gathers them
    # via the search, so the action reliably re-enters review every time.
    existing_id = col.decks.id_for_name(name)
    reuse = existing_id is not None and col.decks.is_filtered(existing_id)
    deck = col.sched.get_or_create_filtered_deck(
        deck_id=existing_id if reuse else DeckId(0)
    )
    deck.name = name
    config = deck.config
    config.reschedule = reschedule
    del config.search_terms[:]
    config.search_terms.append(
        FilteredDeckConfig.SearchTerm(search=search, limit=limit, order=order)  # type: ignore[arg-type]
    )
    try:
        out = col.sched.add_or_update_filtered_deck(deck)
    except FilteredDeckError:
        # The backend refuses to build a filtered deck with no matching cards.
        tooltip(f"No cards to study for “{name}”.", parent=mw)
        return False
    did = DeckId(out.id)

    if not col.decks.card_count(did, include_subdecks=False):
        # Defensive: nothing was gathered — drop the empty deck, report honestly.
        col.decks.remove([did])
        tooltip(f"No cards to study for “{name}”.", parent=mw)
        mw.reset()
        return False

    col.decks.select(did)
    mw.reset()
    mw.moveToState("review")
    return True


def study_ethics_pairs(mw: AnkiQt) -> None:
    """Filter to the CFA::Ethics Pairs deck and open the reviewer.

    Self-healing: if the deck is missing/empty (e.g. it was never preloaded),
    seed the 30 shipped ethics pairs on demand and enter review — never a
    dead-end pointing at a non-existent menu item.
    """
    if not mw.col:
        return
    try:
        search = f'deck:"{ETHICS_DECK_NAME}"'
        name = "CFA::Study — Ethics Minimal-Pairs"
        if _study_filtered_deck(mw, name=name, search=search, order=0):
            return  # oldest seen first — cards were present, we're studying

        # No ethics cards yet — preload the shipped bank on demand, then retry.
        from aqt.cfa_seed import ensure_ethics_deck

        added = ensure_ethics_deck(mw.col)
        if added:
            tooltip(f"Loaded {added} CFA Ethics pairs — starting review.", parent=mw)
            mw.reset()
        if _study_filtered_deck(mw, name=name, search=search, order=0):
            return

        # Still couldn't enter review. Only claim the deck is "not available in
        # this build" when the ethics cards genuinely do not exist — never when
        # they clearly do (the reuse/rebuild above makes that the normal case).
        # This keeps the message honest and rules out the false dead-end.
        ethics_id = mw.col.decks.id_for_name(ETHICS_DECK_NAME)
        have_cards = ethics_id is not None and bool(
            mw.col.decks.card_count(ethics_id, include_subdecks=True)
        )
        if have_cards:
            tooltip("No ethics cards are available to study right now.", parent=mw)
        else:
            showInfo(
                "The CFA::Ethics Pairs deck is not available in this build, so "
                "there is nothing to study yet.",
                parent=mw,
            )
    except Exception as exc:  # pragma: no cover - surfaced to the user, no crash
        showWarning(f"Could not start ethics study: {exc}", parent=mw)


def study_ethics_passages(mw: AnkiQt) -> None:
    """Seed the ``CFA::Ethics Passages`` one-passage deck on demand and study it.

    This makes the F1 one-passage flagship reachable on desktop. Unlike the
    minimal-pairs sibling (which studies via a *filtered* deck), the passages
    deck is a NORMAL deck, so entering review is Anki's own study path: ensure
    the deck exists (seed if missing) → select it → move into the reviewer.

    Re-entrant by construction:

    * ``ensure_ethics_passages_deck`` is idempotent (a no-op once the passages
      are present), so a repeat invocation never duplicates the deck or cards.
    * Re-selecting an already-selected deck and re-entering review is harmless.

    The "not available in this build" modal is only shown when the passages
    genuinely cannot be seeded (deck sources absent in this build) — never when
    the deck already exists with cards, so there is no false dead-end.
    """
    col = mw.col
    if not col:
        return
    try:
        # Seed on demand if the deck is missing/empty. Idempotent: once the
        # passages are present this returns 0 and changes nothing, so calling
        # the action twice never duplicates the deck or its cards.
        from aqt.cfa_seed import ensure_ethics_passages_deck

        added = ensure_ethics_passages_deck(col)
        if added:
            tooltip(f"Loaded {added} CFA Ethics passages — starting review.", parent=mw)
            mw.reset()

        did = col.decks.id_for_name(ETHICS_PASSAGES_DECK_NAME)
        have_cards = did is not None and bool(
            col.decks.card_count(did, include_subdecks=True)
        )
        if did is None or not have_cards:
            # Only claim "not available in this build" when the passages truly
            # cannot be seeded (sources missing) — never when the deck exists
            # with cards. This keeps the message honest and rules out the false
            # dead-end modal the sibling action was recently fixed to avoid.
            showInfo(
                "The CFA::Ethics Passages deck is not available in this build, so "
                "there is nothing to study yet.",
                parent=mw,
            )
            return

        # Normal (non-filtered) deck: select it and move Anki into the reviewer,
        # the same entry point as the overview "Study" button. reset() refreshes
        # the scheduler queues so freshly-seeded NEW cards are picked up.
        col.decks.select(did)
        mw.reset()
        mw.moveToState("review")
    except Exception as exc:  # pragma: no cover - surfaced to the user, no crash
        showWarning(f"Could not start ethics passages study: {exc}", parent=mw)


def study_by_exam_priority(mw: AnkiQt) -> None:
    """Build the exam-priority queue and open a filtered deck in that order.

    Scoped to the current deck; on the built-in "Default" deck an empty
    deck-scoped queue falls back to the whole collection
    (:func:`cfa.build_exam_queue_all_decks`) so a fresh profile still has cards
    to study.
    """
    col = mw.col
    if not col:
        return
    try:
        deck_id = col.decks.get_current_id()
        queue = cfa.build_exam_queue(col, deck_id=deck_id, fetch_limit=200)
        card_ids = list(getattr(queue, "card_ids", []))
        on_default_deck = deck_id == DEFAULT_DECK_ID
        if not card_ids and on_default_deck:
            # Only the built-in "Default" deck falls back to the whole
            # collection. On a fresh profile the current deck is that empty
            # Default deck (the first-launch seeder creates the CFA decks but
            # never selects one), so a deck-scoped queue is empty even though
            # every NEW CFA card — treated as maximally weak (R=0) — is waiting
            # in the CFA decks. Widening the scope only here lets exam-priority
            # bootstrap a fresh profile without silently hijacking a user who
            # deliberately selected and then finished a specific deck.
            queue = cfa.build_exam_queue_all_decks(col, fetch_limit=200)
            card_ids = list(getattr(queue, "card_ids", []))
        if not card_ids:
            if on_default_deck:
                showInfo(
                    "There are no studyable cards for the exam-priority queue "
                    "right now — every card is suspended, buried, or already "
                    "being studied in a filtered deck.",
                    parent=mw,
                )
            else:
                showInfo(
                    "This deck has no studyable cards for the exam-priority "
                    "queue — every card is either suspended, buried, or already "
                    "being studied in a filtered deck. Switch to a deck with "
                    "cards, or select the Default deck to span the whole "
                    "collection.",
                    parent=mw,
                )
            return
        # Preserve the RPC's priority order via an explicit cid list; the
        # filtered deck keeps that order (order index 5 == "Order added").
        cid_search = "(cid:" + ",".join(str(c) for c in card_ids) + ")"
        # The exam-priority queue deliberately includes NEW (never-studied)
        # cards — treated as maximally weak (R=0) — so a fresh deck is never
        # empty. Report that honestly so the count isn't mistaken for "due".
        new_count = len(col.find_cards(f"({cid_search}) is:new"))
        if _study_filtered_deck(
            mw,
            name=EXAM_PRIORITY_DECK_NAME,
            search=cid_search,
            order=5,  # "Order added" — respects our priority ordering
            limit=len(card_ids),
        ):
            tooltip(
                f"Exam-priority queue: {len(card_ids)} cards weakest-first "
                f"(including {new_count} new).",
                parent=mw,
            )
    except Exception as exc:  # pragma: no cover - surfaced to the user, no crash
        showWarning(f"Could not build the exam-priority queue: {exc}", parent=mw)


def _default_exam_date() -> str:
    """A sensible CFA exam-day default used when none has been configured yet.

    Uses the fork's canonical Level II sitting if it is still in the future;
    otherwise falls back to ~120 days out so the deadline view is always usable.
    """
    from datetime import date, timedelta

    canonical = date(2026, 8, 25)
    today = date.today()
    target = canonical if canonical > today else today + timedelta(days=120)
    return target.isoformat()


# A persisted exam date more than this many days in the future is treated as
# runtime pollution (e.g. a stale/absurd far-future date) rather than a real
# sitting, and self-healed back to the canonical default. Two years is a
# generous ceiling — it keeps even a far-out real sitting a candidate might pick
# while still flagging multi-year garbage like the observed 2028-08-23 date.
_MAX_EXAM_HORIZON_DAYS = 730


def _sanitized_exam_date(iso: str | None, *, today: date | None = None) -> str:
    """Return a trustworthy ISO exam date, self-healing absurd persisted values.

    The exam date lives in the synced collection config, so a stale or corrupt
    value can be persisted and then trusted blindly — e.g. an observed
    far-future ``2028-08-23`` that long predates this profile's real sitting.
    This guards the read: a missing, unparseable, or unreasonably-far-future
    date (more than ``_MAX_EXAM_HORIZON_DAYS`` ahead of ``today``) falls back to
    the canonical :func:`_default_exam_date` (the fork's 2026-08-25 sitting);
    any sane date is returned untouched.
    """
    from datetime import date as _date

    if not iso:
        return _default_exam_date()
    try:
        parsed = _date.fromisoformat(iso)
    except ValueError:
        return _default_exam_date()
    reference = today or _date.today()
    if (parsed - reference).days > _MAX_EXAM_HORIZON_DAYS:
        return _default_exam_date()
    return iso


def show_deadline(mw: AnkiQt) -> None:
    """Open the Peak-on-Exam-Day view (with an exam-date picker).

    No dead-end when no exam date is set: the dialog defaults to a sensible CFA
    exam day and lets the learner pick one, persisting it via set_exam_config.
    """
    col = mw.col
    if not col:
        return
    try:
        DeadlineDialog(mw).exec()
    except Exception as exc:  # pragma: no cover - surfaced to the user, no crash
        showWarning(f"Could not open the deadline view: {exc}", parent=mw)


class ExamReadinessDialog(QDialog):
    """Exam Readiness surface — a thin host for the SvelteKit page.

    The honest-score presentation (the Bayesian pass/fail hero, the three
    give-up-gated bands, the per-topic recall table) now lives in the shared
    ``ts/lib/cfa`` design system and is served by mediasrv from the SAME
    ``anki.cfa`` data the old Qt body rendered (see
    ``mediasrv._cfa_exam_readiness_payload``). This dialog just embeds that page
    for the given deck; the window title and size are unchanged.
    """

    def __init__(self, mw: AnkiQt, deck_id: DeckId) -> None:
        super().__init__(mw)
        assert mw.col is not None
        self.setWindowTitle("CFA — Exam Readiness")
        # Wide enough that the three value-first StatCards render their serif
        # ranges (e.g. "82%–100%") on a single line at real desktop width.
        self.resize(800, 600)
        self.web: AnkiWebView | None = AnkiWebView(kind=AnkiWebViewKind.CFA_READINESS)
        self.web.load_sveltekit_page(f"cfa-readiness/{int(deck_id)}")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)

    def _cleanup_web(self) -> None:
        if self.web is not None:
            self.web.cleanup()
            self.web = None

    def reject(self) -> None:
        self._cleanup_web()
        super().reject()


class DeadlineDialog(QDialog):
    """Peak-on-Exam-Day (Deadline) surface — a thin host for the SvelteKit page.

    The exam-date picker and the weakest-first ranking now live in the shared
    ``ts/lib/cfa`` design system; committing a date persists it via the
    ``SetCfaExamDate`` RPC and re-runs the ranking. The page is scoped to the
    current deck — the same deck the old Qt body ranked (see
    ``mediasrv._cfa_deadline_payload``). Window title and size are unchanged.
    """

    def __init__(self, mw: AnkiQt) -> None:
        super().__init__(mw)
        self.mw = mw
        col = mw.col
        assert col is not None
        self.setWindowTitle("CFA — Peak-on-Exam-Day (Deadline)")
        self.resize(560, 500)
        deck_id = col.decks.get_current_id()
        self.web: AnkiWebView | None = AnkiWebView(kind=AnkiWebViewKind.CFA_DEADLINE)
        self.web.load_sveltekit_page(f"cfa-deadline/{int(deck_id)}")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)

    def _cleanup_web(self) -> None:
        if self.web is not None:
            self.web.cleanup()
            self.web = None

    def reject(self) -> None:
        self._cleanup_web()
        super().reject()
