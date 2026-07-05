# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork — seed a *populated* review history into the CFA Level II deck.

The honest CFA scores (memory / performance / readiness) deliberately ABSTAIN
until there is a defensible amount of evidence (see ``pylib/anki/cfa.py``:
``MIN_GRADED_REVIEWS`` = 200 graded reviews, ``MIN_TOPIC_COVERAGE`` = 50%,
``MIN_FIRST_EXPOSURES`` = 30, and no high-weight topic skipped). A fresh
profile therefore renders the honest first-run *abstain* state.

To capture the **populated** render of the desktop Readiness / Home surfaces —
real score ranges + a lit-up coverage map, the state a returning learner sees —
we need a collection whose review history has crossed every threshold. This
module does exactly that on an already-open collection, deterministically and
without any AI:

* it walks every configured exam topic (``los::<slug>`` prefix), picks a fixed
  slice of that topic's cards, gives them FSRS memory state, and writes graded
  ``revlog`` rows on *distinct days* (so the engine's per-(card, day) anti-cram
  dedupe does not collapse them);
* it spreads reviews across **all** topics so coverage is 100% and no
  high-weight topic is skipped;
* the mix is ~70% correct (ease 3) / ~30% incorrect (ease 1) so the performance
  Wilson interval and memory retrievability are realistic, not a fake 100%.

It is honest evidence, not a fabricated score: the numbers are computed by the
same shared engine from a real (seeded) study history. Used by
``qt/tests/launch_anki_for_e2e.py`` (when ``CFA_SEED_REVIEWS`` is set) to back
the populated-render Playwright capture, and unit-tested directly against the
real ``cfa.readiness_score`` give-up rule.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# Allow ``out/pylib`` / ``pylib`` on the path when imported/run directly.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, "out", "pylib"), os.path.join(_ROOT, "pylib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from anki import cfa  # noqa: E402

# Study-history shape. 10 topics x PER_TOPIC cards x REVIEWS_EACH reviews clears
# 200 graded reviews (>= MIN_GRADED_REVIEWS), 30 first exposures
# (>= MIN_FIRST_EXPOSURES: one per seeded card), and 100% coverage with every
# high-weight topic covered — with comfortable headroom.
PER_TOPIC = 8
REVIEWS_EACH = 4
_DAY_MS = 86_400 * 1000
# Realistic accuracy: fail ~30% of exposures (ease 1), pass the rest (ease 3).
_FAIL_EVERY = 10  # (idx + j) % 10 < 3  -> ~30% incorrect
# FSRS memory state used to give each seeded card a *varied* retrievability so
# the coverage-map recall column spans a realistic band (~68%–92%) instead of a
# degenerate, fake-looking flat 100%. A fixed stability with a per-card elapsed
# interval (elapsed / stability from ~0.3 to ~5) drives the FSRS forgetting
# curve across that range deterministically.
_STABILITY_DAYS = 30.0
_RATIO_STEPS = 16
_RATIO_BASE = 0.3
_RATIO_STEP = 0.32


def _topic_card_ids(col: Any, prefix: str, limit: int) -> list[int]:
    """Up to ``limit`` card ids in scope for a ``los::<slug>`` topic prefix.

    Matches the topic's own tag and any child reading tag
    (``los::ethics`` and ``los::ethics::reading-1``), the same hierarchy the
    memory score joins on.
    """
    query = f'("tag:{prefix}" OR "tag:{prefix}::*")'
    cids = [int(c) for c in col.find_cards(query)]
    cids.sort()
    return cids[:limit]


def seed_review_history(
    col: Any,
    *,
    per_topic: int = PER_TOPIC,
    reviews_each: int = REVIEWS_EACH,
    now: int | None = None,
) -> dict:
    """Write a graded review history that crosses the CFA give-up thresholds.

    Deterministic; safe to call once on a freshly seeded CFA collection. Returns
    a summary dict (topics touched, cards, graded reviews, first exposures).
    Raises ``RuntimeError`` if the resulting history does not clear the abstain
    rule, so a caller can never silently capture a still-abstaining screen.
    """
    import time

    from anki.decks import DeckId

    now = int(now) if now is not None else int(time.time())

    cfg = cfa.get_exam_config(col) or {}
    weights: dict[str, float] = cfg.get("topic_weights", {})
    prefixes = cfa.readiness_topic_prefixes(weights)

    touched_cids: list[int] = []
    per_topic_counts: dict[str, int] = {}
    for prefix in prefixes:
        cids = _topic_card_ids(col, prefix, per_topic)
        per_topic_counts[prefix] = len(cids)
        touched_cids.extend(cids)

    if not touched_cids:
        raise RuntimeError(
            "no CFA cards found to seed reviews on — is the CFA Level II deck "
            "loaded? (call seed_collection first)"
        )

    # Give the touched cards FSRS memory state (so retrievability is defined and
    # each covered topic reports a real recall range) and make them due. Each
    # card gets a distinct elapsed interval against a fixed stability so the
    # FSRS forgetting curve yields a realistic spread of recall (not a flat
    # 100%). Deterministic in (topic index, card index).
    col.sched.set_due_date(touched_cids, "0")
    for ti, prefix in enumerate(prefixes):
        for i, cid in enumerate(_topic_card_ids(col, prefix, per_topic)):
            ratio = _RATIO_BASE + ((ti * 5 + i * 3) % _RATIO_STEPS) * _RATIO_STEP
            ivl = max(1, int(round(ratio * _STABILITY_DAYS)))
            data = json.dumps(
                {"s": _STABILITY_DAYS, "d": 5.0, "lrt": now - ivl * 86_400}
            )
            col.db.execute("update cards set data=?, ivl=? where id=?", data, ivl, cid)

    # Graded reviews on distinct days per card (avoids per-(card, day) dedupe).
    uid = int(col.db.scalar("select count(*) from revlog") or 0)
    base_ms = now * 1000 - reviews_each * _DAY_MS
    rows = []
    for idx, cid in enumerate(touched_cids):
        for j in range(reviews_each):
            ease = 1 if (idx + j) % _FAIL_EVERY < 3 else 3
            rows.append(
                (base_ms + j * _DAY_MS + uid, cid, -1, ease, 10, 5, 2500, 1000, 1)
            )
            uid += 1
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )

    # Verify the give-up rule is now satisfied on the CFA deck — abort loudly if
    # not, so we never advertise a "populated" capture that is still abstaining.
    main_deck = col.decks.id_for_name("CFA Level II")
    deck_id = DeckId(int(main_deck)) if main_deck is not None else None
    mem = cfa.memory_score(col, deck_id=deck_id)
    perf = cfa.performance_score(col, deck_id=deck_id)
    rdy = cfa.readiness_score(col, deck_id=deck_id)
    if mem.abstain or perf.abstain or rdy.abstain:
        raise RuntimeError(
            "seeded history still abstains "
            f"(memory={mem.reason!r} performance={perf.reason!r} "
            f"readiness={rdy.reason!r}); increase per_topic/reviews_each"
        )

    return {
        "topics": len([p for p, n in per_topic_counts.items() if n]),
        "cards": len(touched_cids),
        "graded_reviews": len(rows),
        "first_exposures": len(touched_cids),
        "deck_id": int(main_deck) if main_deck is not None else None,
        "memory_point": mem.point,
        "performance_point": perf.point,
        "readiness_point": rdy.point,
        "coverage_pct": mem.coverage_pct,
    }
