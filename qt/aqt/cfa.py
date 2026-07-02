# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork: desktop UI surface for the honest memory score.

Adds a "CFA" menu with an "Exam Readiness" dialog that reports the per-topic
FSRS retrievability as a range (never a bare number) and enforces the give-up
rule, showing "not enough data" until there is enough evidence. No AI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from anki import cfa
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

if TYPE_CHECKING:
    from aqt.main import AnkiQt


def setup_menu(mw: AnkiQt) -> None:
    """Add a top-level CFA menu to the main window."""
    menu = QMenu("&CFA", mw)
    action = menu.addAction("Exam Readiness…")
    qconnect(action.triggered, lambda: show_exam_readiness(mw))
    mw.form.menubar.addMenu(menu)


def show_exam_readiness(mw: AnkiQt) -> None:
    if not mw.col:
        return
    deck_id = mw.col.decks.get_current_id()
    ExamReadinessDialog(mw, deck_id).exec()


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


class ExamReadinessDialog(QDialog):
    def __init__(self, mw: AnkiQt, deck_id: DeckId) -> None:
        super().__init__(mw)
        col = mw.col
        assert col is not None
        self.setWindowTitle("CFA — Exam Readiness")
        self.resize(640, 460)
        layout = QVBoxLayout(self)

        score = cfa.memory_score(col, deck_id=deck_id)
        deck_name = col.decks.name(deck_id)

        header = QLabel()
        header.setTextFormat(Qt.TextFormat.RichText)
        if score.abstain:
            header.setText(
                f"<h2>{deck_name}</h2>"
                "<p style='color:#b45309;font-size:15px'><b>Not enough data</b></p>"
                f"<p>{score.reason}</p>"
                f"<p>Coverage {_pct(score.coverage_pct)} "
                f"({score.topics_covered}/{score.topics_total} topics) · "
                f"{score.graded_reviews} graded reviews</p>"
            )
        else:
            header.setText(
                f"<h2>{deck_name}</h2>"
                "<p style='font-size:15px'>Recall probability "
                "(unweighted mean across covered topics): "
                f"<b>{_pct(score.range_low)}–{_pct(score.range_high)}</b> "
                f"<span style='color:#666'>(midpoint {_pct(score.point)})</span></p>"
                f"<p>Coverage {_pct(score.coverage_pct)} "
                f"({score.topics_covered}/{score.topics_total} topics) · "
                f"{score.graded_reviews} graded reviews · "
                f"as of {score.last_review_at or '—'}</p>"
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
            "Score shown only after ≥200 graded reviews AND ≥50% topic coverage; "
            "abstains if a high-weight topic is skipped. Range = mean ± spread of "
            "per-topic FSRS retrievability. No AI — pure spaced-repetition stats."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color:#666;font-size:11px")
        layout.addWidget(footer)
