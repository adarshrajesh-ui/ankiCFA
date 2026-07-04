#!/usr/bin/env python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Author a hand-written CFA Level II deck from ``cfa/deck/*.jsonl``.

Creates a "CFA Level II" deck whose notes are tagged with hierarchical
``los::<topic>::<reading>`` tags — the join key used by the exam-queue engine
and the memory score — and persists representative per-topic exam weights.

Content is hand-authored (there is no AI/generation anywhere in this app). Each
row in ``cfa/deck/*.jsonl`` is an original, authored item carrying a
``license: authored-original`` marker; no copyrighted CFA Institute material is
used. The item files together are a representative slice of the CFA Level II
topic areas (all ten of them), not the full curriculum.

Every built card carries a visible NAMED SOURCE footer (its CFA Level II topic +
the specific reading it drills, derived from the ``los::`` tag) so a study card's
provenance mirrors the app's AI provenance line -- see :func:`render_source_line`.

Deck size vs. session size: the authored deck is >200 cards. The "Study by Exam
Priority" queue does not shrink the deck -- it returns a *capped, weakest-first
fetch* (a ``fetch_limit`` session cap, e.g. desktop 50-200, mobile 100) drawn
from the full deck. Any small per-session card count is that fetch limit, never
the deck size.

Usage:
    out/pyenv/bin/python tools/cfa/build_cfa_deck.py --path /tmp/cfa.anki2
    out/pyenv/bin/python tools/cfa/build_cfa_deck.py --path /tmp/cfa.anki2 --apkg /tmp/cfa.apkg
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

# Repo root (three levels up from tools/cfa/build_cfa_deck.py).
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECK_DIR = os.path.join(REPO, "cfa", "deck")

# Canonical deck + exam identity, reused by the first-launch seeder so desktop
# and tests share one source of truth.
MAIN_DECK_NAME = "CFA Level II"
DEFAULT_EXAM_DATE = "2026-08-25"  # a representative CFA Level II sitting

# The fields every authored item row must carry.
REQUIRED_FIELDS = {"front", "back", "topic", "los_tag", "source", "license"}

# Base CFA Level II topic weights (midpoints of the published ranges), keyed by
# the ``los::<topic>`` prefix used in the item files. Only the prefixes actually
# present in the loaded items are used, and they are renormalized to sum to 1.0
# so the exam-queue engine and memory score always see a valid distribution.
BASE_TOPIC_WEIGHTS: dict[str, float] = {
    "los::ethics": 0.12,
    "los::quant": 0.08,
    "los::econ": 0.08,
    "los::fra": 0.12,
    "los::corp": 0.08,
    "los::equity": 0.12,
    "los::fixed-income": 0.12,
    "los::derivatives": 0.08,
    "los::altinv": 0.08,
    "los::portmgmt": 0.12,
}


def los_prefix(los_tag: str) -> str:
    """Return the ``los::<topic>`` prefix (first two segments) of a tag."""
    return "::".join(los_tag.split("::")[:2])


# --- Content-type classification (Brainlift POV3) -----------------------------
# Every card is tagged with exactly one ``type::<kind>`` tag from this closed
# set. The exam-queue engine multiplies a card's score by a per-type interval
# multiplier (see anki.cfa.DEFAULT_TYPE_MULTIPLIERS), so equally-weak cards of
# different item types are prioritized differently. Classification is a
# deterministic keyword heuristic over the authored front/back text.
ITEM_TYPES = (
    "formula",
    "ethics-rule",
    "conceptual",
    "multi-step-calc",
    "case-application",
)

_CALC_CUES = ("calculate", "compute", "solve for", "how much", "work out")
_FORMULA_CUES = (
    "write the",
    "write out",
    "express",
    "formula",
    "equation",
    "state the",
    "notation",
)
_CASE_CUES = (
    "an analyst",
    "an investor",
    "a portfolio manager",
    "a firm",
    "a company",
    "suppose",
    "scenario",
    "given that",
    "consider a",
)


def classify_item_type(item: dict[str, str]) -> str:
    """Return the ``type::<kind>`` content type for an authored item.

    Deterministic keyword heuristic, evaluated in priority order so each item
    maps to exactly one of :data:`ITEM_TYPES`:

    1. ``ethics-rule``      — any Ethics/Standards topic (needs frequent reinforcement)
    2. ``multi-step-calc``  — asks to calculate/compute/solve a value
    3. ``formula``          — asks to state/write an equation, or the answer is one
    4. ``case-application`` — an actor/scenario the candidate must reason about
    5. ``conceptual``       — everything else (definitions, distinctions)
    """
    front = item["front"].lower()

    if los_prefix(item["los_tag"]) == "los::ethics":
        return "ethics-rule"
    if any(cue in front for cue in _CALC_CUES):
        return "multi-step-calc"
    if any(cue in front for cue in _FORMULA_CUES) or ("=" in item["back"]):
        return "formula"
    if any(cue in front for cue in _CASE_CUES):
        return "case-application"
    return "conceptual"


def load_items(deck_dir: str = DECK_DIR) -> list[dict[str, str]]:
    """Load and de-duplicate all authored items from ``deck_dir/*.jsonl``.

    Rows whose front was already seen (case-insensitive) are skipped so the
    built deck has no duplicate first fields. Raises ``ValueError`` on a
    malformed row (invalid JSON, missing/extra field, empty value, or a
    ``los_tag`` that does not start with ``los::``) so a bad item file fails
    loudly at build time.
    """
    items: list[dict[str, str]] = []
    seen_fronts: set[str] = set()
    for path in sorted(glob.glob(os.path.join(deck_dir, "*.jsonl"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                if not raw.strip():
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{name}:{lineno}: invalid JSON ({exc})") from exc
                if not isinstance(obj, dict):
                    raise ValueError(f"{name}:{lineno}: row is not a JSON object")
                if set(obj) != REQUIRED_FIELDS:
                    raise ValueError(
                        f"{name}:{lineno}: fields {sorted(obj)} != {sorted(REQUIRED_FIELDS)}"
                    )
                for key, value in obj.items():
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"{name}:{lineno}: empty/non-string {key!r}")
                if not obj["los_tag"].startswith("los::"):
                    raise ValueError(
                        f"{name}:{lineno}: los_tag must start with 'los::'"
                    )
                key = obj["front"].strip().lower()
                if key in seen_fronts:
                    continue
                seen_fronts.add(key)
                items.append(obj)
    return items


def topic_weights_for(items: list[dict[str, str]]) -> dict[str, float]:
    """Renormalized topic weights over the ``los::`` prefixes present in items."""
    present = {los_prefix(i["los_tag"]) for i in items}
    weights = {p: BASE_TOPIC_WEIGHTS[p] for p in present if p in BASE_TOPIC_WEIGHTS}
    total = sum(weights.values())
    if not total:
        return {}
    return {p: round(w / total, 4) for p, w in weights.items()}


# --- Named source provenance (Brainlift D1) ----------------------------------
# Every AI output in this app carries a named source; a hand-authored STUDY card
# gets the same treatment. The named source is the item's topic + the specific
# CFA Level II reading it drills, derived deterministically from the ``los::``
# tag (the join key), so a learner can always see *where a card comes from*.
SOURCE_PREFIX = "Source:"


def reading_from_los(los_tag: str) -> str:
    """Human-readable reading name from the ``los::<topic>::<reading>`` tag.

    ``los::fixed-income::term-structure-forward-rates`` -> ``term structure
    forward rates``; a deeper tag joins its trailing segments with `` / ``.
    """
    parts = los_tag.split("::")
    reading = " / ".join(
        seg.replace("-", " ").strip() for seg in parts[2:] if seg.strip()
    )
    return reading


def render_source_line(item: dict[str, str]) -> str:
    """A visible, deterministic named source for a built study card.

    Example: ``Source: CFA Level II > Fixed Income > term structure forward
    rates``. Appended to the card Back (additive, never replacing authored
    content) so the study-card provenance mirrors the app's AI provenance line.
    """
    reading = reading_from_los(item["los_tag"])
    tail = f" > {reading}" if reading else ""
    return f"{SOURCE_PREFIX} CFA Level II > {item['topic']}{tail}"


def back_with_source(item: dict[str, str]) -> str:
    """The card Back with its named-source footer appended (HTML-safe)."""
    return (
        f"{item['back']}<br><br>"
        f'<span class="cfa-source">{render_source_line(item)}</span>'
    )


def add_deck_notes(col, deck_dir: str = DECK_DIR) -> dict:
    """Add the authored CFA Level II notes + exam config to an OPEN collection.

    Idempotency is the caller's concern (the seeder skips a deck that already
    has cards); this always appends. Returns a summary dict with the number of
    notes added and the topic weights persisted.
    """
    from anki import cfa

    items = load_items(deck_dir)
    weights = topic_weights_for(items)

    deck_id = col.decks.id(MAIN_DECK_NAME)
    assert deck_id is not None
    notetype = col.models.by_name("Basic")

    added = 0
    for item in items:
        note = col.new_note(notetype)
        note["Front"] = item["front"]
        # Additive named-source footer (Brainlift D1): every study card shows the
        # CFA Level II topic + reading it drills, derived from its ``los::`` tag.
        note["Back"] = back_with_source(item)
        note.tags = [item["los_tag"], f"type::{classify_item_type(item)}"]
        col.add_note(note, deck_id)
        added += 1

    cfa.set_exam_config(
        col,
        exam_date=DEFAULT_EXAM_DATE,
        topic_weights=weights,
    )
    return {"notes_added": added, "topic_weights": weights, "deck_id": deck_id}


def build(path: str, apkg: str | None) -> int:
    # Ensure the built pylib is importable when run from the repo.
    for p in ("pylib", "out/pylib"):
        full = os.path.join(REPO, p)
        if full not in sys.path:
            sys.path.insert(0, full)

    from anki.collection import Collection
    from anki.exporting import AnkiPackageExporter

    col = Collection(path)
    try:
        stats = add_deck_notes(col)
        added = stats["notes_added"]
        weights = stats["topic_weights"]
        deck_id = stats["deck_id"]

        print(
            f"Added {added} notes across {len(weights)} topics to '{MAIN_DECK_NAME}'."
        )
        print(f"Exam config stored (exam_date + {len(weights)} topic weights).")

        if apkg:
            exporter = AnkiPackageExporter(col)
            exporter.did = deck_id
            exporter.exportInto(apkg)
            print(f"Exported deck to {apkg}")
    finally:
        col.close()
    return added


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a hand-authored CFA Level II deck.")
    ap.add_argument(
        "--path", required=True, help="Path to the .anki2 collection to write into."
    )
    ap.add_argument("--apkg", help="Optional path to also export an .apkg for import.")
    args = ap.parse_args()
    build(args.path, args.apkg)


if __name__ == "__main__":
    main()
