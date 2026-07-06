#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork — A9: one-command latency benchmark on a ~50k-card deck.

Builds a realistic ~50,000-card CFA collection (10 canonical topics, a slice of
studied review cards with FSRS memory state + graded revlog, the rest new) in a
throwaway temp collection, then times the hot user-facing operations against the
**real built backend** and reports **p50 / p95 / worst-case** latency for each:

    * ``next-card``            — ``sched.get_queued_cards`` (fetch the next card)
    * ``answerCard ack``       — ``sched.answer_card`` (grade + dequeue)
    * ``dashboard first load`` — cold ``compute_cfa_scores`` (whole collection)
    * ``dashboard refresh``    — warm repeated ``compute_cfa_scores``
    * ``sync``                 — a real incremental ``sync_collection`` round
                                 against a local ``anki-sync-server`` subprocess

Everything runs offline against a local sync server; no AI and no network are
required. ``just bench`` runs the full 50k deck; ``just bench-smoke`` runs a
small deck for CI. Sync is best-effort: if the local sync-server subprocess
cannot start it is reported ``BLOCKED`` with the root cause rather than faked.

This is a MEASUREMENT of the real engine, not a simulation — numbers vary with
the host machine, so we report the machine and the sample sizes alongside them.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
import time
from dataclasses import dataclass, field

# Allow ``out/pylib`` / ``pylib`` on the path when run directly.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, "out", "pylib"), os.path.join(_ROOT, "pylib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from anki import cfa  # noqa: E402
from anki.cards import CardId  # noqa: E402
from anki.collection import Collection  # noqa: E402
from anki.decks import DeckId  # noqa: E402

DEFAULT_CARDS = 50_000
DEFAULT_REPS = 400
# Fraction of the deck that is a studied review card (the rest stay new).
STUDIED_FRACTION = 0.35
REVIEWS_EACH = 3


# --- statistics --------------------------------------------------------------


def _percentile(sorted_vals: list[float], pct: float) -> float:
    """Nearest-rank percentile of an already-sorted list (pct in [0, 100])."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    # nearest-rank: rank = ceil(pct/100 * N), clamped to [1, N]
    import math

    rank = max(1, min(len(sorted_vals), math.ceil(pct / 100.0 * len(sorted_vals))))
    return sorted_vals[rank - 1]


@dataclass
class Stat:
    """p50 / p95 / worst summary of a set of latency samples (milliseconds)."""

    name: str
    samples_ms: list[float] = field(default_factory=list)
    note: str = ""

    @property
    def n(self) -> int:
        return len(self.samples_ms)

    @property
    def p50(self) -> float:
        return _percentile(sorted(self.samples_ms), 50)

    @property
    def p95(self) -> float:
        return _percentile(sorted(self.samples_ms), 95)

    @property
    def worst(self) -> float:
        return max(self.samples_ms) if self.samples_ms else float("nan")

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "n": self.n,
            "p50_ms": None if self.n == 0 else round(self.p50, 3),
            "p95_ms": None if self.n == 0 else round(self.p95, 3),
            "worst_ms": None if self.n == 0 else round(self.worst, 3),
            "note": self.note,
        }


# --- deck construction -------------------------------------------------------


def build_deck(col: Collection, n_cards: int) -> DeckId:
    """Create ``n_cards`` CFA cards spread across the 10 canonical topics.

    A ``STUDIED_FRACTION`` slice becomes due review cards with FSRS memory state
    and ``REVIEWS_EACH`` graded reviews apiece (so the scheduler has real due
    cards and the score engine has real accuracy data); the rest stay new.
    Uses batched ``add_note`` plus direct-DB revlog writes for speed.
    """
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    topics = cfa.CANONICAL_TOPICS
    now = int(time.time())

    studied_target = int(n_cards * STUDIED_FRACTION)
    studied_cids: list[CardId] = []
    for i in range(n_cards):
        topic = topics[i % len(topics)]
        note = col.new_note(nt)
        note["Front"] = f"{topic}-q{i}"
        note["Back"] = f"answer-{i}"
        # mix in a content-type tag so the type-weighting path is exercised too
        type_tag = "type::formula" if i % 3 == 0 else "type::concept"
        note.tags = [f"{topic}::r1", type_tag]
        col.add_note(note, deck)
        if len(studied_cids) < studied_target:
            studied_cids.append(col.find_cards(f"nid:{note.id}")[0])

    # Turn the studied slice into due review cards with FSRS memory state.
    if studied_cids:
        col.sched.set_due_date(studied_cids, "0")
        data = json.dumps({"s": 60.0, "d": 5.0, "lrt": now - 86400})
        col.db.executemany(
            "update cards set data=? where id=?",
            [(data, c) for c in studied_cids],
        )
        # graded reviews on distinct days per card (avoids (card, day) dedupe)
        day_ms = 86_400 * 1000
        base_ms = now * 1000 - REVIEWS_EACH * day_ms
        uid = col.db.scalar("select count(*) from revlog") or 0
        rows = []
        for idx, c in enumerate(studied_cids):
            # ~70% correct (ease 3), ~30% wrong (ease 1) for realistic accuracy
            for j in range(REVIEWS_EACH):
                ease = 1 if (idx + j) % 10 < 3 else 3
                rows.append(
                    (base_ms + j * day_ms + uid, c, -1, ease, 10, 5, 2500, 1000, 1)
                )
                uid += 1
        col.db.executemany(
            "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
            " values (?,?,?,?,?,?,?,?,?)",
            rows,
        )

    # Select the CFA deck and lift the per-day new/review caps so the review
    # loop can actually pull a long stream of due cards to time.
    col.decks.select(deck)
    conf = col.decks.config_dict_for_deck_id(deck)
    # Anki clamps per-day limits at 9999; anything larger makes update_config a
    # silent no-op (leaving the default 200/20 caps), so clamp explicitly.
    cap = min(n_cards, 9999)
    conf["new"]["perDay"] = cap
    conf["rev"]["perDay"] = cap
    col.decks.update_config(conf)
    col.save()
    return deck


# --- benchmark passes --------------------------------------------------------


def bench_review_loop(col: Collection, reps: int) -> tuple[Stat, Stat]:
    """Time ``get_queued_cards`` (next-card) and ``answer_card`` (ack) reps."""
    from anki.cards import Card
    from anki.scheduler.v3 import CardAnswer

    next_stat = Stat("next-card", note="sched.get_queued_cards(fetch_limit=1)")
    ack_stat = Stat("answerCard ack", note="sched.answer_card (GOOD)")

    for _ in range(reps):
        t0 = time.perf_counter()
        queued = col.sched.get_queued_cards(fetch_limit=1)  # type: ignore[union-attr]
        next_stat.samples_ms.append((time.perf_counter() - t0) * 1000.0)
        if not queued.cards:
            break
        qc = queued.cards[0]
        card = Card(col)
        card._load_from_backend_card(qc.card)
        card.start_timer()
        states = col._backend.get_scheduling_states(card.id)
        answer = col.sched.build_answer(  # type: ignore[union-attr]
            card=card, states=states, rating=CardAnswer.GOOD
        )
        t0 = time.perf_counter()
        col.sched.answer_card(answer)  # type: ignore[union-attr]
        ack_stat.samples_ms.append((time.perf_counter() - t0) * 1000.0)
    return next_stat, ack_stat


def bench_dashboard(col: Collection, refresh_reps: int) -> tuple[Stat, Stat]:
    """Time the CFA readiness dashboard: cold first load + warm refreshes.

    A single ``compute_cfa_scores`` RPC returns memory + performance + readiness
    — exactly what the dashboard renders — so we time that whole-collection RPC.
    """
    first = Stat(
        "dashboard first load",
        note="compute_cfa_scores whole-collection (cold)",
    )
    refresh = Stat(
        "dashboard refresh",
        note="compute_cfa_scores whole-collection (warm)",
    )

    def _one() -> None:
        col._backend.compute_cfa_scores(deck_id=0, whole_collection=True, now=0)

    t0 = time.perf_counter()
    _one()
    first.samples_ms.append((time.perf_counter() - t0) * 1000.0)
    for _ in range(refresh_reps):
        t0 = time.perf_counter()
        _one()
        refresh.samples_ms.append((time.perf_counter() - t0) * 1000.0)
    return first, refresh


def bench_sync(col_path: str, reps: int) -> Stat:
    """Time a real incremental sync round against a local anki-sync-server.

    Full-uploads the collection once (warm-up, not timed), then makes a tiny
    change and times each incremental ``sync_collection`` round. Best-effort: on
    any server/subprocess failure returns a Stat carrying a BLOCKED note rather
    than fabricating a number.
    """
    stat = Stat("sync", note="incremental sync_collection vs local anki-sync-server")
    try:
        from anki import cfa_sync as cs
    except Exception as exc:  # pragma: no cover - import guard
        stat.note = f"BLOCKED: cannot import cfa_sync ({exc})"
        return stat

    srv_base = tempfile.mkdtemp(prefix="cfa-bench-sync-")
    try:
        with cs.sync_server(srv_base) as server:
            from anki.cards import Card
            from anki.scheduler.v3 import CardAnswer

            col = Collection(col_path)
            try:
                auth = cs.login(col, server)
                # First sync of a fresh remote → full upload (warm-up, untimed).
                cs.force_full_upload(col, auth)
                outcomes = []
                for _ in range(reps):
                    # Grade one real due card through the backend so there is a
                    # genuine incremental change (card + revlog) to push.
                    queued = col.sched.get_queued_cards(fetch_limit=1)  # type: ignore[union-attr]
                    if queued.cards:
                        qc = queued.cards[0]
                        card = Card(col)
                        card._load_from_backend_card(qc.card)
                        card.start_timer()
                        states = col._backend.get_scheduling_states(card.id)
                        col.sched.answer_card(  # type: ignore[union-attr]
                            col.sched.build_answer(  # type: ignore[union-attr]
                                card=card, states=states, rating=CardAnswer.GOOD
                            )
                        )
                    t0 = time.perf_counter()
                    outcomes.append(cs.sync(col, auth))
                    stat.samples_ms.append((time.perf_counter() - t0) * 1000.0)
                # Confirm these were genuine incremental (NORMAL) syncs, not
                # server-forced full transfers — honesty about what we measured.
                incremental = {cs.NO_CHANGES, cs.NORMAL_SYNC}
                normal = sum(1 for o in outcomes if o in incremental)
                stat.note += f" [{normal}/{len(outcomes)} normal/no-change rounds]"
            finally:
                col.close()
    except Exception as exc:
        stat.samples_ms.clear()
        stat.note = f"BLOCKED: sync-server round failed ({type(exc).__name__}: {exc})"
    return stat


# --- reporting ---------------------------------------------------------------


def format_report(stats: list[Stat], meta: dict) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("CFA A9 — 50k-card latency benchmark (REAL backend, no AI, offline)")
    lines.append("=" * 72)
    lines.append(f"cards       : {meta['cards']:,}")
    lines.append(
        f"studied     : {meta['studied']:,} review cards ({REVIEWS_EACH} reviews each)"
    )
    lines.append(f"review reps : {meta['reps']}")
    lines.append(f"machine     : {meta['machine']}")
    lines.append(f"build time  : {meta['build_s']:.2f}s")
    lines.append("")
    lines.append(
        f"{'operation':<24}{'n':>5}{'p50 (ms)':>12}{'p95 (ms)':>12}{'worst (ms)':>13}"
    )
    lines.append("-" * 72)
    for s in stats:
        if s.n == 0:
            lines.append(f"{s.name:<24}{'-':>5}{'-':>12}{'-':>12}{'-':>13}")
            lines.append(f"    {s.note}")
        else:
            lines.append(
                f"{s.name:<24}{s.n:>5}{s.p50:>12.3f}{s.p95:>12.3f}{s.worst:>13.3f}"
            )
    lines.append("-" * 72)
    lines.append("Notes:")
    for s in stats:
        if s.note:
            lines.append(f"  * {s.name}: {s.note}")
    lines.append("=" * 72)
    return "\n".join(lines)


def run_benchmark(
    n_cards: int, reps: int, do_sync: bool, sync_reps: int
) -> tuple[list[Stat], dict]:
    workdir = tempfile.mkdtemp(prefix="cfa-bench-")
    col_path = os.path.join(workdir, "bench.anki2")
    col = Collection(col_path)
    t0 = time.perf_counter()
    build_deck(col, n_cards)
    build_s = time.perf_counter() - t0
    studied = int(n_cards * STUDIED_FRACTION)

    next_stat, ack_stat = bench_review_loop(col, reps)
    first_stat, refresh_stat = bench_dashboard(col, max(3, min(reps, 50)))
    col.close()

    stats = [next_stat, ack_stat, first_stat, refresh_stat]
    if do_sync:
        stats.append(bench_sync(col_path, sync_reps))
    else:
        stats.append(Stat("sync", note="SKIPPED (--no-sync)"))

    meta = {
        "cards": n_cards,
        "studied": studied,
        "reps": reps,
        "build_s": build_s,
        "machine": f"{platform.system()} {platform.machine()} "
        f"py{platform.python_version()}",
    }
    return stats, meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CFA A9 50k-card latency benchmark")
    ap.add_argument("--cards", type=int, default=DEFAULT_CARDS)
    ap.add_argument("--reps", type=int, default=DEFAULT_REPS)
    ap.add_argument("--sync-reps", type=int, default=5)
    ap.add_argument("--no-sync", action="store_true", help="skip the sync round")
    ap.add_argument(
        "--smoke",
        action="store_true",
        help="tiny deck for CI (600 cards, 60 reps, no sync)",
    )
    ap.add_argument("--json", action="store_true", help="also print a JSON blob")
    args = ap.parse_args(argv)

    if args.smoke:
        n_cards, reps, do_sync = 600, 60, False
    else:
        n_cards, reps, do_sync = args.cards, args.reps, not args.no_sync

    stats, meta = run_benchmark(n_cards, reps, do_sync, args.sync_reps)
    print(format_report(stats, meta))
    if args.json:
        print(json.dumps({"meta": meta, "stats": [s.as_dict() for s in stats]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
