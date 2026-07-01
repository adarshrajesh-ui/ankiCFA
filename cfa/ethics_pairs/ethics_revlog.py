# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Read pair attempts from a collection's review log into AttemptRecord objects.

Import-safe without a built pylib: this module never imports ``anki`` at top level; it only calls
methods on a live ``Collection`` passed in by the caller (the add-on or the offline dashboard).

Mapping (deterministic): the card template auto-rates a pair Good (ease 3) when it is fully correct
and Again (ease 1) when it is not, so ``ease >= 3`` means "fully correct". Only genuine answers
(revlog.type in learn/review/relearn = 0/1/2) are counted; manual/cram/reschedule rows are ignored.
Because the revlog syncs across AnkiWeb/AnkiDroid/AnkiMobile, this reflects reviews from any device.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ethics_notetype as _nt  # noqa: E402
from ethics_scoring import AttemptRecord  # noqa: E402

_CLUSTER_PREFIX = "cluster::"
# Anki revlog.type values that represent a real graded answer.
_REAL_ANSWER_TYPES = (0, 1, 2)  # learn, review, relearn


def cluster_from_tags(tags: str) -> str | None:
    """Extract the ``cluster::<id>`` value from a space-separated Anki tag string."""
    for tag in (tags or "").split():
        if tag.startswith(_CLUSTER_PREFIX):
            return tag[len(_CLUSTER_PREFIX) :]
    return None


def read_attempts(col, deck_name: str = _nt.DECK_NAME) -> list[AttemptRecord]:
    """Return one AttemptRecord per graded review of a pair card in ``deck_name`` (and subdecks)."""
    card_ids = list(col.find_cards(f'deck:"{deck_name}"'))
    if not card_ids:
        return []

    placeholders = ",".join(["?"] * len(card_ids))
    rows = col.db.all(
        f"""
        select revlog.id, revlog.ease, notes.tags
        from revlog
        join cards on revlog.cid = cards.id
        join notes on cards.nid = notes.id
        where revlog.cid in ({placeholders})
          and revlog.type in ({",".join(str(t) for t in _REAL_ANSWER_TYPES)})
          and revlog.ease between 1 and 4
        order by revlog.id asc
        """,
        *card_ids,
    )

    records: list[AttemptRecord] = []
    for revlog_id, ease, tags in rows:
        cluster = cluster_from_tags(tags)
        if cluster is None:
            continue
        records.append(
            AttemptRecord(cluster=cluster, correct=ease >= 3, order=int(revlog_id))
        )
    return records
