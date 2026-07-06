# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Phase-0 parity proof: the Rust ComputeCfaScores RPC == pylib/anki/cfa.py.

Builds a collection with day-spaced graded reviews (one review per card per
day, the realistic review-card case where the (card,day) de-dup is a no-op),
then asserts the RPC-backed scores equal the pure-Python cfa.py reference to
1e-9. Also proves the double-count fix on a same-day-duplicate card.
"""

import json
import os
import sys
import tempfile

import anki.cfa as cfa
from anki.collection import Collection

DAY_MS = 86_400_000
TOL = 1e-9


def add_card(col, deck_id, nt, front, topic):
    note = col.new_note(nt)
    note["Front"] = front
    note["Back"] = "answer"
    note.tags = [f"{topic}::r1"]
    col.add_note(note, deck_id)
    return col.find_cards(f"nid:{note.id}")[0]


def seed_topic(col, deck, nt, topic, n_cards, stability, reviews_each, first_ease, now_ms, salt):
    """Each card: FSRS memory state + `reviews_each` reviews on DISTINCT days.

    `salt` offsets the within-day component so ids never collide across topics."""
    now = now_ms // 1000
    cids = [add_card(col, deck, nt, f"{topic}-{i}", topic) for i in range(n_cards)]
    col.sched.set_due_date(cids, "0")
    data = json.dumps({"s": stability, "d": 5.0, "lrt": now - 86400})
    col.db.executemany(
        "update cards set data=?, ivl=? where id=?", [(data, 20, c) for c in cids]
    )
    rows = []
    start_ms = now_ms - reviews_each * DAY_MS
    for idx, c in enumerate(cids):
        for j in range(reviews_each):
            # j=0 is the oldest -> the "first exposure"; each j a distinct day;
            # idx+salt keeps ids globally unique without crossing a day boundary.
            rid = start_ms + j * DAY_MS + idx + salt
            ease = first_ease[idx] if j == 0 else 3
            rows.append((rid, c, -1, ease, 10, 5, 2500, 1000, 1))
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return cids


def seed_rich(col, now_ms):
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    seed_topic(col, deck, nt, "los::topica", 20, 2000.0, 6, [3] * 20, now_ms, salt=0)
    seed_topic(col, deck, nt, "los::topicb", 20, 8.0, 6, [3] * 10 + [1] * 10, now_ms, salt=1000)
    cfa.set_exam_config(
        col, exam_date="2026-12-01", topic_weights={"los::topica": 0.9, "los::topicb": 0.1}
    )
    return deck


def opt(msg, field):
    """proto3 optional -> None when unset, else the value."""
    return getattr(msg, field) if msg.HasField(field) else None


FAILURES = []


def eq(label, a, b):
    ok = (a == b) if not (isinstance(a, float) and isinstance(b, float)) else abs(a - b) < TOL
    if a is None or b is None:
        ok = a is None and b is None
    if not ok:
        FAILURES.append(f"{label}: py={a!r} rpc={b!r}")


def cmp_num(label, a, b):
    if a is None or b is None:
        if not (a is None and b is None):
            FAILURES.append(f"{label}: py={a!r} rpc={b!r}")
        return
    if abs(a - b) >= TOL:
        FAILURES.append(f"{label}: py={a!r} rpc={b!r} (|d|={abs(a-b):.2e})")


def main():
    path = os.path.join(tempfile.mkdtemp(), "c.anki2")
    col = Collection(path)
    now_ms = 1_760_000_000_000  # pinned, well after all seed days
    now = now_ms // 1000
    deck = seed_rich(col, now_ms)

    # --- reference (pure Python) ---
    py_mem = cfa.memory_score(col, deck_id=deck, now_ts=now)
    py_perf = cfa.performance_score(col, deck_id=deck, now_ts=now)
    py_ready = cfa.readiness_score(col, deck_id=deck, now_ts=now)
    py_bayes = cfa.bayesian_readiness(col, deck_id=deck, now_ts=now)

    # --- RPC (shared Rust engine) ---
    r = col.backend.compute_cfa_scores(deck_id=int(deck), whole_collection=False, now=now)
    rm, rp, rr, rb = r.memory, r.performance, r.readiness, r.bayesian

    print("=== reference cfa.py ===")
    print(f"  memory: abstain={py_mem.abstain} point={py_mem.point} reviews={py_mem.graded_reviews}")
    print(f"  perf:   point={py_perf.point} first={py_perf.first_exposures} correct={py_perf.correct}")
    print(f"  ready:  point={py_ready.point}")
    print(f"  bayes:  acc={py_bayes.accuracy} p_pass={py_bayes.p_pass} call={py_bayes.call!r}")
    print("=== RPC ===")
    print(f"  memory: abstain={rm.abstain} point={opt(rm,'point')} reviews={rm.graded_reviews}")
    print(f"  perf:   point={opt(rp,'point')} first={rp.first_exposures} correct={rp.correct}")
    print(f"  ready:  point={opt(rr,'point')}")
    print(f"  bayes:  acc={rb.accuracy} p_pass={rb.p_pass} call={rb.call!r}")

    # --- memory ---
    eq("mem.abstain", py_mem.abstain, rm.abstain)
    eq("mem.reason", py_mem.reason, rm.reason)
    cmp_num("mem.point", py_mem.point, opt(rm, "point"))
    cmp_num("mem.range_low", py_mem.range_low, opt(rm, "range_low"))
    cmp_num("mem.range_high", py_mem.range_high, opt(rm, "range_high"))
    cmp_num("mem.coverage_pct", py_mem.coverage_pct, rm.coverage_pct)
    eq("mem.topics_total", py_mem.topics_total, rm.topics_total)
    eq("mem.topics_covered", py_mem.topics_covered, rm.topics_covered)
    eq("mem.graded_reviews", py_mem.graded_reviews, rm.graded_reviews)
    eq("mem.last_review_at", py_mem.last_review_at, opt(rm, "last_review_at"))
    eq("mem.computed_at", py_mem.computed_at, rm.computed_at)
    rm_by = {t.topic: t for t in rm.topics}
    for t in py_mem.topics:
        rt = rm_by[t.topic]
        cmp_num(f"mem[{t.topic}].weight", t.weight, rt.weight)
        eq(f"mem[{t.topic}].reviewed_cards", t.reviewed_cards, rt.reviewed_cards)
        eq(f"mem[{t.topic}].graded_reviews", t.graded_reviews, rt.graded_reviews)
        cmp_num(f"mem[{t.topic}].avg_r", t.avg_r, opt(rt, "avg_r"))
        cmp_num(f"mem[{t.topic}].r_low", t.r_low, opt(rt, "r_low"))
        cmp_num(f"mem[{t.topic}].r_high", t.r_high, opt(rt, "r_high"))
        eq(f"mem[{t.topic}].covered", t.covered, rt.covered)

    # --- performance ---
    eq("perf.abstain", py_perf.abstain, rp.abstain)
    cmp_num("perf.point", py_perf.point, opt(rp, "point"))
    cmp_num("perf.range_low", py_perf.range_low, opt(rp, "range_low"))
    cmp_num("perf.range_high", py_perf.range_high, opt(rp, "range_high"))
    eq("perf.first_exposures", py_perf.first_exposures, rp.first_exposures)
    eq("perf.correct", py_perf.correct, rp.correct)

    # --- readiness ---
    eq("ready.abstain", py_ready.abstain, rr.abstain)
    cmp_num("ready.point", py_ready.point, opt(rr, "point"))
    cmp_num("ready.range_low", py_ready.range_low, opt(rr, "range_low"))
    cmp_num("ready.range_high", py_ready.range_high, opt(rr, "range_high"))
    eq("ready.label", py_ready.label, rr.label)
    cmp_num("ready.memory_point", py_ready.memory_point, opt(rr, "memory_point"))
    cmp_num("ready.performance_point", py_ready.performance_point, opt(rr, "performance_point"))
    cmp_num("ready.coverage_pct", py_ready.coverage_pct, rr.coverage_pct)

    # --- bayesian ---
    cmp_num("bayes.accuracy", py_bayes.accuracy, rb.accuracy)
    cmp_num("bayes.ci_low", py_bayes.ci_low, rb.ci_low)
    cmp_num("bayes.ci_high", py_bayes.ci_high, rb.ci_high)
    eq("bayes.call", py_bayes.call, rb.call)
    cmp_num("bayes.call_prob", py_bayes.call_prob, rb.call_prob)
    cmp_num("bayes.p_pass", py_bayes.p_pass, rb.p_pass)
    cmp_num("bayes.mps", py_bayes.mps, rb.mps)
    cmp_num("bayes.recall", py_bayes.recall, opt(rb, "recall"))
    eq("bayes.first_exposures", py_bayes.first_exposures, rb.first_exposures)
    eq("bayes.topics_covered", py_bayes.topics_covered, rb.topics_covered)
    rb_by = {t.topic: t for t in rb.topics}
    for t in py_bayes.topics:
        bt = rb_by[t.topic]
        eq(f"bayes[{t.topic}].successes", t.successes, bt.successes)
        eq(f"bayes[{t.topic}].failures", t.failures, bt.failures)
        cmp_num(f"bayes[{t.topic}].mean", t.mean, bt.mean)
        cmp_num(f"bayes[{t.topic}].ci_low", t.ci_low, bt.ci_low)
        cmp_num(f"bayes[{t.topic}].ci_high", t.ci_high, bt.ci_high)
        cmp_num(f"bayes[{t.topic}].recall", t.recall, opt(bt, "recall"))

    # --- double-count fix (D4): two same-day reviews count once via the RPC ---
    dup_cid = add_card(col, deck, col.models.by_name("Basic"), "dup", "los::topica")
    col.sched.set_due_date([dup_cid], "0")
    col.db.execute(
        "update cards set data=?, ivl=? where id=?",
        json.dumps({"s": 100.0, "d": 5.0, "lrt": now - 86400}), 20, dup_cid,
    )
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        [(now_ms, dup_cid, -1, 3, 10, 5, 2500, 1000, 1),
         (now_ms - 1000, dup_cid, -1, 3, 10, 5, 2500, 1000, 1)],
    )
    r2 = col.backend.compute_cfa_scores(deck_id=int(deck), whole_collection=False, now=now)
    dup_topic = {t.topic: t for t in r2.memory.topics}["los::topica"]
    naive = col.db.scalar("select count(*) from revlog where cid=?", dup_cid)
    # This card contributes exactly ONE graded-review day despite two rows.
    delta = dup_topic.graded_reviews - {t.topic: t for t in rm.topics}["los::topica"].graded_reviews
    print(f"\n=== double-count fix: dup card has {naive} revlog rows, "
          f"adds {delta} to the topic count (fix works: {delta == 1}) ===")
    if delta != 1:
        FAILURES.append(f"double-count: dup card added {delta} (expected 1)")

    col.close()

    print()
    if FAILURES:
        print(f"PARITY FAILED: {len(FAILURES)} mismatch(es):")
        for f in FAILURES:
            print("  -", f)
        sys.exit(1)
    print("PARITY PASSED: RPC == cfa.py on every field (tol 1e-9), double-count fixed.")


main()
