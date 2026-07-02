# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork: idempotent first-launch seeder.

Seeds an OPEN collection with the two CFA study decks and the exam config so a
fresh Anki profile boots straight into a study-ready CFA Level II collection:

* ``CFA Level II``       — the authored deck (cfa/deck/*.jsonl)
* ``CFA::Ethics Pairs``  — the ethics minimal-pairs tap-to-highlight deck
* the persisted exam config (exam date + per-topic weights)

The seeder is IDEMPOTENT: it skips any deck that already has cards, so it never
re-imports or clobbers existing study data. This is the single seeding path
shared by the desktop first-run hook (``aqt.cfa_seed``) and its pytest.

No AI — pure deck authoring + spaced-repetition config.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_import_paths(repo: str) -> None:
    """Make the deck builder and ethics importer reachable regardless of CWD."""
    for rel in ("tools/cfa", "cfa/ethics_pairs", "pylib", "out/pylib"):
        full = os.path.join(repo, rel)
        if os.path.isdir(full) and full not in sys.path:
            sys.path.insert(0, full)


def _deck_has_cards(col: Any, name: str) -> bool:
    """True if a deck by ``name`` exists AND currently holds at least one card."""
    did = col.decks.id_for_name(name)
    if did is None:
        return False
    return bool(col.decks.card_count(did, include_subdecks=True))


def seed_collection(col: Any, *, repo_root: str | None = None) -> dict:
    """Idempotently seed ``col`` with the CFA decks + exam config.

    Returns a summary dict describing what was added and what was skipped. Safe
    to call on every launch: decks that already have cards are left untouched.
    """
    repo = repo_root or _repo_root()
    _ensure_import_paths(repo)

    import build_cfa_deck  # tools/cfa
    import import_pairs  # cfa/ethics_pairs

    from anki import cfa

    summary: dict[str, Any] = {
        "main_deck": build_cfa_deck.MAIN_DECK_NAME,
        "ethics_deck": import_pairs.nt.DECK_NAME,
        "main_seeded": False,
        "ethics_seeded": False,
        "notes_added": 0,
        "ethics_added": 0,
        "config_set": False,
    }

    # --- Main CFA Level II deck ------------------------------------------------
    # Note whether a config already existed BEFORE we seed, so the summary is
    # honest about whether this run stored it (add_deck_notes sets it too).
    had_config = bool(cfa.get_exam_config(col))

    if _deck_has_cards(col, build_cfa_deck.MAIN_DECK_NAME):
        summary["main_skipped"] = "deck already has cards"
    else:
        stats = build_cfa_deck.add_deck_notes(col)
        summary["main_seeded"] = True
        summary["notes_added"] = stats["notes_added"]
        summary["config_set"] = True  # add_deck_notes persisted the exam config

    # Store the exam config if one is still not persisted (main deck pre-existed).
    if had_config:
        summary["config_skipped"] = "exam config already present"
    elif not summary["config_set"]:
        # Main deck existed but config missing: derive weights from the deck
        # source items so the exam-queue engine still sees a valid distribution.
        items = build_cfa_deck.load_items()
        cfa.set_exam_config(
            col,
            exam_date=build_cfa_deck.DEFAULT_EXAM_DATE,
            topic_weights=build_cfa_deck.topic_weights_for(items),
        )
        summary["config_set"] = True

    # --- Ethics minimal-pairs deck --------------------------------------------
    if _deck_has_cards(col, import_pairs.nt.DECK_NAME):
        summary["ethics_skipped"] = "deck already has cards"
    else:
        pairs = import_pairs.load_pairs()
        estats = import_pairs.import_pairs(col, pairs)
        summary["ethics_seeded"] = True
        summary["ethics_added"] = estats["total"]

    return summary


def _main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Idempotently seed a collection with the CFA decks."
    )
    ap.add_argument(
        "--path", required=True, help="Path to the .anki2 collection to seed."
    )
    args = ap.parse_args(argv)

    repo = _repo_root()
    _ensure_import_paths(repo)
    from anki.collection import Collection

    col = Collection(args.path)
    try:
        summary = seed_collection(col)
    finally:
        col.close()

    print(
        f"seed: main_seeded={summary['main_seeded']} "
        f"(+{summary['notes_added']} notes), "
        f"ethics_seeded={summary['ethics_seeded']} "
        f"(+{summary['ethics_added']} cards), "
        f"config_set={summary['config_set']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
