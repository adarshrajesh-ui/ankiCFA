# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Phase-0 parity gate: the shared Rust ``ComputeCfaScores`` engine (which the
public :mod:`anki.cfa` functions delegate to, and which the AnkiDroid client
calls) must equal the pure-Python reference (``anki.cfa._py_*``) field-by-field
to 1e-9. This is what makes "desktop == mobile == old Python" true.

It also pins the intentional divergence: the Rust engine de-duplicates graded
reviews to at most one per (card, day), so a same-day duplicate (an offline
dual-device round-trip) is counted once by the RPC while the naive raw count
would double it.

Skips cleanly when the loaded backend predates the RPC (an older ``_rsbridge``),
so it never spuriously fails an out-of-date build.
"""

from __future__ import annotations

import json
import time

import pytest

from anki import cfa
from anki.collection import Collection
from tests.shared import getEmptyCol

DAY_MS = 86_400 * 1000
TOL = 1e-9


def _rpc_available(col: Collection) -> bool:
    return hasattr(col._backend, "compute_cfa_scores")


def _add_card(col, deck_id, nt, front, topic):
    note = col.new_note(nt)
    note["Front"] = front
    note["Back"] = "answer"
    note.tags = [f"{topic}::r1"]
    col.add_note(note, deck_id)
    return col.find_cards(f"nid:{note.id}")[0]


def _seed_topic(col, deck, nt, topic, n_cards, stability, reviews_each, first_ease, now):
    """`n_cards` review cards with FSRS memory + `reviews_each` reviews on
    DISTINCT days (dedup is a no-op here so raw == de-duplicated)."""
    cids = [_add_card(col, deck, nt, f"{topic}-{i}", topic) for i in range(n_cards)]
    col.sched.set_due_date(cids, "0")
    data = json.dumps({"s": stability, "d": 5.0, "lrt": now - 86400})
    col.db.executemany("update cards set data=?, ivl=? where id=?", [(data, 20, c) for c in cids])
    base_ms = now * 1000 - reviews_each * DAY_MS
    uid = col.db.scalar("select count(*) from revlog") or 0
    rows = []
    for idx, c in enumerate(cids):
        for j in range(reviews_each):
            ease = first_ease[idx] if j == 0 else 3
            rows.append((base_ms + j * DAY_MS + uid, c, -1, ease, 10, 5, 2500, 1000, 1))
            uid += 1
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return cids


def _seed_rich(col, now):
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    _seed_topic(col, deck, nt, "los::topica", 20, 2000.0, 6, [3] * 20, now)
    _seed_topic(col, deck, nt, "los::topicb", 20, 8.0, 6, [3] * 10 + [1] * 10, now)
    cfa.set_exam_config(
        col, exam_date="2026-12-01", topic_weights={"los::topica": 0.9, "los::topicb": 0.1}
    )
    return deck


def _close(py_val, rpc_val, label):
    if py_val is None or rpc_val is None:
        assert py_val is None and rpc_val is None, f"{label}: {py_val!r} vs {rpc_val!r}"
    elif isinstance(py_val, float):
        assert abs(py_val - rpc_val) < TOL, f"{label}: {py_val!r} vs {rpc_val!r}"
    else:
        assert py_val == rpc_val, f"{label}: {py_val!r} vs {rpc_val!r}"


def test_rpc_matches_python_reference_field_by_field():
    col = getEmptyCol()
    if not _rpc_available(col):
        pytest.skip("backend predates ComputeCfaScores RPC; rebuild pylib")
    now = int(time.time())
    deck = _seed_rich(col, now)

    for name in ("memory_score", "performance_score", "readiness_score", "bayesian_readiness"):
        py = getattr(cfa, f"_py_{name}")(col, deck_id=deck, now_ts=now)
        rpc = getattr(cfa, name)(col, deck_id=deck, now_ts=now)
        for field in vars(py):
            if field == "topics":
                continue
            _close(getattr(py, field), getattr(rpc, field), f"{name}.{field}")
        # per-topic breakdowns
        py_t = {t.topic: t for t in getattr(py, "topics", [])}
        rpc_t = {t.topic: t for t in getattr(rpc, "topics", [])}
        assert py_t.keys() == rpc_t.keys(), f"{name}: topic sets differ"
        for topic, py_topic in py_t.items():
            for field in vars(py_topic):
                _close(
                    getattr(py_topic, field),
                    getattr(rpc_t[topic], field),
                    f"{name}[{topic}].{field}",
                )
    col.close()


def test_rpc_dedups_same_day_reviews_but_python_reference_does_not():
    col = getEmptyCol()
    if not _rpc_available(col):
        pytest.skip("backend predates ComputeCfaScores RPC; rebuild pylib")
    now = int(time.time())
    deck = _seed_rich(col, now)
    nt = col.models.by_name("Basic")
    dup = _add_card(col, deck, nt, "dup", "los::topica")
    col.sched.set_due_date([dup], "0")
    col.db.execute(
        "update cards set data=?, ivl=? where id=?",
        json.dumps({"s": 100.0, "d": 5.0, "lrt": now - 86400}), 20, dup,
    )
    now_ms = now * 1000
    # two graded reviews on the SAME day (a dual-device round-trip)
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        [(now_ms, dup, -1, 3, 10, 5, 2500, 1000, 1),
         (now_ms - 1000, dup, -1, 3, 10, 5, 2500, 1000, 1)],
    )
    py = cfa._py_memory_score(col, deck_id=deck, now_ts=now)
    rpc = cfa.memory_score(col, deck_id=deck, now_ts=now)
    py_a = {t.topic: t for t in py.topics}["los::topica"].graded_reviews
    rpc_a = {t.topic: t for t in rpc.topics}["los::topica"].graded_reviews
    # The RPC counts the dup card once; the naive Python reference counts it twice.
    assert rpc_a == py_a - 1, f"expected dedup by 1: py={py_a} rpc={rpc_a}"
    col.close()
