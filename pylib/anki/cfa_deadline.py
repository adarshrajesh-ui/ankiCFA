# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork (DOK-4): deadline retention — peak recall on the exam date.

FSRS optimises the least-cost schedule for *indefinite* retention; the CFA exam
instead needs peak retention on ONE date. This module wraps the read-only Rust
``DeadlineRetention`` RPC, which for a deck + exam date:

* predicts each due card's FSRS retrievability **at the exam date** (reusing the
  same engine retrievability function used everywhere else), and
* suggests a next interval capped at ``min(FSRS interval, days_to_exam)`` so no
  review is ever scheduled past the exam.

Cards come back sorted by lowest predicted exam-day recall first, surfacing the
cards most likely to be weak *on the day*.

The Rust RPC is the source of truth. Until the freshly-added RPC binding has been
compiled into the running backend (i.e. before a full ``just build`` regenerates
``scheduler_pb2`` and ``_rsbridge``), this module transparently falls back to an
**equivalent read-only** computation that calls the very same engine FSRS
function (``extract_fsrs_retrievability``) evaluated at the exam instant. Both
paths are non-mutating, so FSRS scheduling and undo stay valid.

There is NO AI here — pure spaced-repetition statistics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Union

import anki.collection
from anki.decks import DeckId

SECS_PER_DAY = 86_400

ExamDate = Union[str, int, float]


@dataclass
class DeadlineRetention:
    """Parallel-array result, sorted by predicted exam-day recall ascending
    (weakest first); ties broken by ascending card id for determinism."""

    card_ids: list[int] = field(default_factory=list)
    # Predicted FSRS retrievability at the exam date, in [0, 1], per card.
    predicted_recall: list[float] = field(default_factory=list)
    # Deadline-capped next interval in days = min(FSRS interval, days_to_exam).
    suggested_interval_days: list[int] = field(default_factory=list)
    # True when served by the Rust RPC; False when served by the SQL fallback.
    used_rpc: bool = False

    def __len__(self) -> int:
        return len(self.card_ids)


def exam_timestamp(exam_date: ExamDate) -> int:
    """Coerce an ISO ``YYYY-MM-DD`` string or Unix seconds into Unix seconds."""
    if isinstance(exam_date, str):
        d = date.fromisoformat(exam_date)
        return int(datetime(d.year, d.month, d.day).timestamp())
    return int(exam_date)


def days_to_exam(exam_ts: int, *, now: Optional[int] = None) -> int:
    """Whole (signed) days from ``now`` until the exam; negative when past."""
    now = now if now is not None else int(time.time())
    return (exam_ts - now) // SECS_PER_DAY


def deadline_retention(
    col: anki.collection.Collection,
    *,
    deck_id: DeckId | int,
    exam_date: ExamDate,
    fetch_limit: int = 0,
    now: Optional[int] = None,
) -> DeadlineRetention:
    """Rank a deck's due cards (subdecks included) by predicted FSRS recall at
    the exam date, each with a deadline-capped next-interval suggestion.

    Prefers the read-only Rust ``DeadlineRetention`` RPC; falls back to an
    equivalent read-only SQL computation when the RPC binding is not present in
    the running backend. Never mutates the collection, so FSRS scheduling and
    the undo history remain valid.
    """
    exam_ts = exam_timestamp(exam_date)
    try:
        return _via_rpc(col, int(deck_id), exam_ts, fetch_limit)
    except (AttributeError, ImportError, NotImplementedError):
        # RPC not compiled into this backend yet — use the parity fallback.
        return _via_sql(col, int(deck_id), exam_ts, fetch_limit, now=now)


def _via_rpc(
    col: anki.collection.Collection, deck_id: int, exam_ts: int, fetch_limit: int
) -> DeadlineRetention:
    resp = col._backend.deadline_retention(
        deck_id=deck_id, exam_date=exam_ts, fetch_limit=fetch_limit
    )
    return DeadlineRetention(
        card_ids=list(resp.card_ids),
        predicted_recall=list(resp.predicted_recall),
        suggested_interval_days=list(resp.suggested_interval_days),
        used_rpc=True,
    )


def _escape_deck_name(name: str) -> str:
    # Escape backslashes and quotes for use inside a deck:"..." search term.
    return name.replace("\\", "\\\\").replace('"', '\\"')


def _via_sql(
    col: anki.collection.Collection,
    deck_id: int,
    exam_ts: int,
    fetch_limit: int,
    *,
    now: Optional[int] = None,
) -> DeadlineRetention:
    now = now if now is not None else int(time.time())
    dte = days_to_exam(exam_ts, now=now)

    # Same card set as the RPC: the deck's (and subdecks') due cards. Using the
    # real search engine keeps the "is:due" semantics identical.
    deck_name = col.decks.name(DeckId(deck_id))
    cids = list(col.find_cards(f'deck:"{_escape_deck_name(deck_name)}" is:due'))
    if not cids:
        return DeadlineRetention(used_rpc=False)

    # Evaluate FSRS retrievability AT the exam instant by passing the exam
    # timestamp as "now" (and the exam-day day-count as "today" for the rare
    # review card that lacks a stored last-review time). Read-only.
    today_at_exam = int(col.sched.today) + dte
    placeholders = ",".join(["?"] * len(cids))
    rows = col.db.all(
        f"""
        select c.id,
          extract_fsrs_retrievability(
            c.data,
            case when c.odue != 0 then c.odue else c.due end,
            c.ivl, ?, ?, ?),
          c.ivl
        from cards c
        where c.id in ({placeholders})
        """,
        today_at_exam,
        int(col.sched.day_cutoff),
        exam_ts,
        *cids,
    )

    interval_cap = max(0, dte)
    scored = [
        (
            int(cid),
            float(r) if r is not None else 0.0,
            min(int(ivl), interval_cap),
        )
        for (cid, r, ivl) in rows
    ]
    # Weakest predicted exam-day recall first; ties broken by ascending id.
    scored.sort(key=lambda row: (row[1], row[0]))
    if fetch_limit:
        scored = scored[:fetch_limit]

    return DeadlineRetention(
        card_ids=[c for c, _, _ in scored],
        predicted_recall=[r for _, r, _ in scored],
        suggested_interval_days=[i for _, _, i in scored],
        used_rpc=False,
    )
