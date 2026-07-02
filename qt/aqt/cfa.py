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
    QDialog,
    QHeaderView,
    QLabel,
    QMenu,
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
    """Filter to the CFA::Ethics Pairs deck and open the reviewer."""
    if not mw.col:
        return
    try:
        search = f'deck:"{ETHICS_DECK_NAME}"'
        if not _study_filtered_deck(
            mw,
            name="CFA::Study — Ethics Minimal-Pairs",
            search=search,
            order=0,  # oldest seen first
        ):
            showInfo(
                "The CFA::Ethics Pairs deck has no due cards yet. Import the "
                "ethics pairs deck first (CFA → deck pre-loading).",
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
                "No cards are currently eligible for the exam-priority queue "
                "in this deck.",
                parent=mw,
            )
            return
        # Preserve the RPC's priority order via an explicit cid list; the
        # filtered deck keeps that order (order index 5 == "Order added").
        cid_search = "(cid:" + ",".join(str(c) for c in card_ids) + ")"
        _study_filtered_deck(
            mw,
            name=EXAM_PRIORITY_DECK_NAME,
            search=cid_search,
            order=5,  # "Order added" — respects our priority ordering
            limit=len(card_ids),
        )
    except Exception as exc:  # pragma: no cover - surfaced to the user, no crash
        showWarning(f"Could not build the exam-priority queue: {exc}", parent=mw)


def show_deadline(mw: AnkiQt) -> None:
    """Show the top weak cards ranked by predicted recall at the exam date."""
    col = mw.col
    if not col:
        return
    try:
        cfg = cfa.get_exam_config(col) or {}
        exam_date = cfg.get("exam_date")
        if not exam_date:
            showInfo(
                "No exam date is configured yet. Set one via the CFA exam "
                "config before using the deadline view.",
                parent=mw,
            )
            return
        deck_id = col.decks.get_current_id()
        result = cfa_deadline.deadline_retention(
            col, deck_id=deck_id, exam_date=exam_date, fetch_limit=50
        )
        DeadlineDialog(mw, result, exam_date=exam_date).exec()
    except Exception as exc:  # pragma: no cover - surfaced to the user, no crash
        showWarning(f"Could not compute deadline retention: {exc}", parent=mw)


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
    """Read-only view of the weakest cards by predicted recall AT the exam date."""

    def __init__(
        self,
        mw: AnkiQt,
        result: cfa_deadline.DeadlineRetention,
        *,
        exam_date: str,
    ) -> None:
        super().__init__(mw)
        self.setWindowTitle("CFA — Peak-on-Exam-Day (Deadline)")
        self.resize(560, 460)
        layout = QVBoxLayout(self)

        source = "Rust RPC" if result.used_rpc else "read-only fallback"
        header = QLabel()
        header.setTextFormat(Qt.TextFormat.RichText)
        if not len(result):
            header.setText(
                "<h2>Peak-on-Exam-Day</h2>"
                "<p style='color:#b45309'><b>No due cards to rank</b></p>"
                f"<p>Exam date: {exam_date}</p>"
            )
        else:
            header.setText(
                "<h2>Peak-on-Exam-Day</h2>"
                f"<p>Exam date: <b>{exam_date}</b> · "
                f"{len(result)} cards ranked weakest-first ({source})</p>"
                "<p style='color:#666'>Predicted FSRS recall AT the exam date; "
                "each interval is capped so no review lands after the exam.</p>"
            )
        header.setWordWrap(True)
        layout.addWidget(header)

        table = QTableWidget(len(result), 3, self)
        table.setHorizontalHeaderLabels(
            ["Card ID", "Predicted recall @ exam", "Capped interval (days)"]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
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
                table.setItem(row, column, item)
        layout.addWidget(table)

        footer = QLabel(
            "Weakest cards on the day are shown first. Study these to peak on the "
            "exam date. Read-only — FSRS scheduling and undo stay valid. No AI."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color:#666;font-size:11px")
        layout.addWidget(footer)
