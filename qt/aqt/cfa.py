# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork: desktop UI surface for the honest memory score.

Adds a "CFA" menu with:

* "Exam Readiness…" — reports the per-topic FSRS retrievability as a range
  (never a bare number) and enforces the give-up rule ("not enough data").
* "Study Ethics Minimal-Pairs" — filters to the ``CFA::Ethics Pairs`` deck and
  opens the reviewer.
* "Study by Exam Priority" — builds the read-only exam-priority queue
  (``build_exam_queue``) and opens a filtered deck ordered by that priority.
* "Peak-on-Exam-Day (Deadline)…" — ranks the current deck's due cards by
  predicted FSRS recall AT the exam date (``cfa_deadline``), weakest first.

No AI — pure spaced-repetition statistics throughout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from anki import cfa, cfa_deadline
from anki.decks import DeckId
from aqt.qt import (
    QAbstractItemView,
    QColor,
    QDate,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    qconnect,
)
from aqt.utils import showInfo, showWarning, tooltip

if TYPE_CHECKING:
    from aqt.main import AnkiQt

# Deck names used by the CFA fork.
ETHICS_DECK_NAME = "CFA::Ethics Pairs"
EXAM_PRIORITY_DECK_NAME = "CFA::Exam Priority"


def setup_menu(mw: AnkiQt) -> None:
    """Add a top-level CFA menu to the main window with four study actions."""
    menu = QMenu("&CFA", mw)

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

    deck = col.sched.get_or_create_filtered_deck(deck_id=DeckId(0))
    deck.name = name
    config = deck.config
    config.reschedule = reschedule
    del config.search_terms[:]
    config.search_terms.append(
        FilteredDeckConfig.SearchTerm(search=search, limit=limit, order=order)
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
        if not _study_filtered_deck(mw, name=name, search=search, order=0):
            showInfo(
                "The CFA::Ethics Pairs deck is not available in this build, so "
                "there is nothing to study yet.",
                parent=mw,
            )
    except Exception as exc:  # pragma: no cover - surfaced to the user, no crash
        showWarning(f"Could not start ethics study: {exc}", parent=mw)


def study_by_exam_priority(mw: AnkiQt) -> None:
    """Build the exam-priority queue and open a filtered deck in that order."""
    col = mw.col
    if not col:
        return
    try:
        deck_id = col.decks.get_current_id()
        queue = cfa.build_exam_queue(col, deck_id=deck_id, fetch_limit=200)
        card_ids = list(getattr(queue, "card_ids", []))
        if not card_ids:
            showInfo(
                "This deck has no studyable cards for the exam-priority queue — "
                "every card is either suspended or in another deck.",
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


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def _band_html(
    name: str, meaning: str, abstain: bool, reason: str, low, high, point
) -> str:
    """Render one honest score as a labelled RANGE (never a bare number)."""
    if abstain:
        return (
            f"<p style='margin:4px 0'><b>{name}</b> "
            f"<span style='color:#666'>— {meaning}</span><br>"
            f"<span style='color:#b45309'><b>Not enough data</b></span> "
            f"<span style='color:#666'>· {reason}</span></p>"
        )
    return (
        f"<p style='margin:4px 0'><b>{name}</b> "
        f"<span style='color:#666'>— {meaning}</span><br>"
        f"<span style='font-size:15px'><b>{_pct(low)}–{_pct(high)}</b></span> "
        f"<span style='color:#666'>(midpoint {_pct(point)})</span></p>"
    )


class ExamReadinessDialog(QDialog):
    def __init__(self, mw: AnkiQt, deck_id: DeckId) -> None:
        super().__init__(mw)
        col = mw.col
        assert col is not None
        self.setWindowTitle("CFA — Exam Readiness")
        self.resize(640, 520)
        layout = QVBoxLayout(self)

        score = cfa.memory_score(col, deck_id=deck_id)
        perf = cfa.performance_score(col, deck_id=deck_id)
        ready = cfa.readiness_score(col, deck_id=deck_id)
        deck_name = col.decks.name(deck_id)

        header = QLabel()
        header.setTextFormat(Qt.TextFormat.RichText)
        header.setText(
            f"<h2>{deck_name}</h2>"
            + _band_html(
                "Memory",
                "recall probability, exam-weighted across topics",
                score.abstain,
                score.reason,
                score.range_low,
                score.range_high,
                score.point,
            )
            + _band_html(
                "Performance",
                "P(correct on a new question), first-exposure accuracy",
                perf.abstain,
                perf.reason,
                perf.range_low,
                perf.range_high,
                perf.point,
            )
            + _band_html(
                f"Readiness — {ready.label}",
                "P(pass); wide range, uncalibrated",
                ready.abstain,
                ready.reason,
                ready.range_low,
                ready.range_high,
                ready.point,
            )
            + (
                f"<p style='color:#666'>Coverage {_pct(score.coverage_pct)} "
                f"({score.topics_covered}/{score.topics_total} topics) · "
                f"{score.graded_reviews} graded reviews · "
                f"{perf.first_exposures} first-seen · "
                f"as of {score.last_review_at or '—'}</p>"
            )
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        table = QTableWidget(len(score.topics), 5, self)
        table.setHorizontalHeaderLabels(
            ["Topic", "Weight", "Reviewed", "Graded", "Recall R (range)"]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for row, t in enumerate(sorted(score.topics, key=lambda x: -x.weight)):
            if t.avg_r is None:
                r_text = "no data"
            else:
                r_text = f"{_pct(t.r_low)}–{_pct(t.r_high)}"
            values = [
                t.topic,
                f"{t.weight:.2f}",
                str(t.reviewed_cards),
                str(t.graded_reviews),
                r_text,
            ]
            for column, val in enumerate(values):
                item = QTableWidgetItem(val)
                if not t.covered and column == 4:
                    item.setForeground(QColor("gray"))
                table.setItem(row, column, item)
        layout.addWidget(table)

        footer = QLabel(
            "Three honest scores, each a RANGE with a give-up rule — never a bare "
            "number. Memory = exam-weighted mean ± spread of per-topic FSRS "
            "retrievability (needs ≥200 graded reviews, ≥50% coverage, no skipped "
            "high-weight topic). Performance = Wilson interval on first-exposure "
            "accuracy (needs ≥30 first-seen questions). Readiness = P(pass) fused "
            "from both, deliberately wide and NOT validated against real exam "
            "data. No AI — pure spaced-repetition stats."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color:#666;font-size:11px")
        layout.addWidget(footer)


class DeadlineDialog(QDialog):
    """Read-only view of the weakest cards by predicted recall AT the exam date.

    Carries a QDateEdit exam-date picker that persists the chosen date via
    ``cfa.set_exam_config`` and re-ranks the cards live. Renders cleanly whether
    or not the deck currently has any due cards.
    """

    def __init__(self, mw: AnkiQt) -> None:
        super().__init__(mw)
        self.mw = mw
        self.setWindowTitle("CFA — Peak-on-Exam-Day (Deadline)")
        self.resize(560, 500)
        layout = QVBoxLayout(self)

        # --- Exam-date picker row ------------------------------------------
        picker = QHBoxLayout()
        picker.addWidget(QLabel("Exam date:"))
        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(self._initial_date())
        picker.addWidget(self.date_edit)
        apply_btn = QPushButton("Set exam date", self)
        qconnect(apply_btn.clicked, self._apply_date)
        picker.addWidget(apply_btn)
        picker.addStretch(1)
        layout.addLayout(picker)

        self._header = QLabel()
        self._header.setTextFormat(Qt.TextFormat.RichText)
        self._header.setWordWrap(True)
        layout.addWidget(self._header)

        self._table = QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels(
            ["Card ID", "Predicted recall @ exam", "Capped interval (days)"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._table)

        footer = QLabel(
            "Weakest cards on the day are shown first. Study these to peak on the "
            "exam date. Read-only — FSRS scheduling and undo stay valid. No AI."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color:#666;font-size:11px")
        layout.addWidget(footer)

        self._reload()

    def _initial_date(self) -> QDate:
        cfg = cfa.get_exam_config(self.mw.col) or {}
        iso = cfg.get("exam_date") or _default_exam_date()
        parsed = QDate.fromString(iso, "yyyy-MM-dd")
        return parsed if parsed.isValid() else QDate.currentDate().addDays(120)

    def _apply_date(self) -> None:
        """Persist the picked exam date (preserving weights) and re-rank."""
        iso = self.date_edit.date().toString("yyyy-MM-dd")
        col = self.mw.col
        assert col is not None
        cfg = cfa.get_exam_config(col) or {}
        cfa.set_exam_config(
            col, exam_date=iso, topic_weights=cfg.get("topic_weights", {})
        )
        tooltip(f"Exam date set to {iso}.", parent=self)
        self._reload()

    def _reload(self) -> None:
        col = self.mw.col
        assert col is not None
        exam_date = self.date_edit.date().toString("yyyy-MM-dd")
        deck_id = col.decks.get_current_id()
        result = cfa_deadline.deadline_retention(
            col, deck_id=deck_id, exam_date=exam_date, fetch_limit=50
        )

        source = "Rust RPC" if result.used_rpc else "read-only fallback"
        if not len(result):
            self._header.setText(
                "<h2>Peak-on-Exam-Day</h2>"
                f"<p>Exam date: <b>{exam_date}</b></p>"
                "<p style='color:#b45309'><b>No due cards to rank yet.</b></p>"
                "<p style='color:#666'>Once this deck has scheduled reviews, "
                "the weakest-on-the-day cards will appear here.</p>"
            )
        else:
            self._header.setText(
                "<h2>Peak-on-Exam-Day</h2>"
                f"<p>Exam date: <b>{exam_date}</b> · "
                f"{len(result)} cards ranked weakest-first ({source})</p>"
                "<p style='color:#666'>Predicted FSRS recall AT the exam date; "
                "each interval is capped so no review lands after the exam.</p>"
            )

        self._table.setRowCount(len(result))
        for row in range(len(result)):
            recall = result.predicted_recall[row]
            values = [
                str(result.card_ids[row]),
                _pct(recall),
                str(result.suggested_interval_days[row]),
            ]
            for column, val in enumerate(values):
                item = QTableWidgetItem(val)
                if column == 1 and recall < 0.85:
                    item.setForeground(QColor("#b45309"))
                self._table.setItem(row, column, item)
