# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork: first-launch deck pre-loading for the desktop app.

On the first load of a fresh profile's collection, seed the CFA Level II deck,
the ethics minimal-pairs deck, and the exam config so the user boots straight
into a study-ready CFA collection. Backed by the shared, idempotent
``tools/cfa/seed_collection.py`` — the same path the pytest exercises.

The seed runs at most once per collection (guarded by a ``cfa_seeded`` config
flag) and never clobbers existing data: decks that already have cards are left
untouched. If the deck sources are unavailable (e.g. a packaged build without
``tools/``), the hook logs and returns without disturbing the profile.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aqt.main import AnkiQt

SEEDED_CONFIG_KEY = "cfa_seeded"


def _repo_root() -> str | None:
    """Locate the fork's repo root (holding ``tools/cfa`` + ``cfa/ethics_pairs``)."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))  # qt/aqt -> qt -> repo
    if os.path.isdir(os.path.join(root, "tools", "cfa")) and os.path.isdir(
        os.path.join(root, "cfa", "ethics_pairs")
    ):
        return root
    return None


def ensure_ethics_deck(col: object) -> int:
    """Idempotently preload the ``CFA::Ethics Pairs`` deck from the shipped bank.

    This is the fork's single most important preload: it guarantees the 30 CFA
    ethics minimal-pairs are present before the learner opens the ethics study
    flow. Returns the number of pairs imported — ``0`` when the deck already has
    cards (idempotent no-op) or when the deck sources are unavailable in this
    build. Never raises; a seeding hiccup must not break the study action.
    """
    repo = _repo_root()
    if not repo:
        return 0
    ethics_dir = os.path.join(repo, "cfa", "ethics_pairs")
    if ethics_dir not in sys.path:
        sys.path.insert(0, ethics_dir)
    try:
        import import_pairs  # type: ignore[import-not-found]  # cfa/ethics_pairs

        deck_name = import_pairs.nt.DECK_NAME
        did = col.decks.id_for_name(deck_name)  # type: ignore[attr-defined]
        if did is not None and col.decks.card_count(  # type: ignore[attr-defined]
            did, include_subdecks=True
        ):
            return 0  # already preloaded — nothing to do
        stats = import_pairs.import_pairs(col, import_pairs.load_pairs())
        return int(stats.get("total", 0))
    except Exception as exc:  # pragma: no cover - defensive; never break study
        print(f"CFA ethics on-demand seeding skipped: {exc}", file=sys.stderr)
        return 0


def ensure_ethics_passages_deck(col: object) -> int:
    """Idempotently preload the ``CFA::Ethics Passages`` one-passage deck.

    Sibling of :func:`ensure_ethics_deck` for the F1 one-passage flagship: it
    guarantees the shipped ethics passages are present before the learner opens
    the one-passage study flow, so that deck is reachable on demand from the
    desktop CFA menu (it is intentionally NOT part of the first-launch seeder).
    Returns the number of passages imported — ``0`` when the deck already has
    cards (idempotent no-op) or when the deck sources are unavailable in this
    build. Never raises; a seeding hiccup must not break the study action.
    """
    repo = _repo_root()
    if not repo:
        return 0
    ethics_dir = os.path.join(repo, "cfa", "ethics_pairs")
    if ethics_dir not in sys.path:
        sys.path.insert(0, ethics_dir)
    try:
        import passages  # type: ignore[import-not-found]  # cfa/ethics_pairs

        deck_name = passages.DECK_NAME
        did = col.decks.id_for_name(deck_name)  # type: ignore[attr-defined]
        if did is not None and col.decks.card_count(  # type: ignore[attr-defined]
            did, include_subdecks=True
        ):
            return 0  # already preloaded — nothing to do
        stats = passages.import_passages(col, passages.load_passages())
        return int(stats.get("total", 0))
    except Exception as exc:  # pragma: no cover - defensive; never break study
        print(f"CFA ethics passages on-demand seeding skipped: {exc}", file=sys.stderr)
        return 0


def maybe_seed(mw: AnkiQt) -> None:
    """Seed the CFA decks on first load of a fresh collection.

    Safe and idempotent: a no-op once ``cfa_seeded`` is set, and even if forced
    the underlying seeder skips decks that already hold cards. Any failure is
    swallowed (logged) so a seeding hiccup never blocks opening the profile.

    The ethics minimal-pairs deck is the priority preload, so if the full
    seeder fails (e.g. a build whose main-deck sources are incomplete) we still
    fall back to preloading the ethics deck on its own.
    """
    col = mw.col
    if not col:
        return
    if col.get_config(SEEDED_CONFIG_KEY, False):
        return

    repo = _repo_root()
    if not repo:
        # Packaged build without deck sources: mark seeded so we don't retry.
        col.set_config(SEEDED_CONFIG_KEY, True)
        return

    tools_cfa = os.path.join(repo, "tools", "cfa")
    if tools_cfa not in sys.path:
        sys.path.insert(0, tools_cfa)

    from aqt.utils import tooltip

    try:
        import seed_collection  # type: ignore[import-not-found]

        summary = seed_collection.seed_collection(col, repo_root=repo)
        col.set_config(SEEDED_CONFIG_KEY, True)
        if summary.get("main_seeded") or summary.get("ethics_seeded"):
            tooltip(
                "CFA decks loaded: "
                f"+{summary.get('notes_added', 0)} CFA Level II cards, "
                f"+{summary.get('ethics_added', 0)} ethics pairs.",
                parent=mw,
            )
    except Exception as exc:  # pragma: no cover - defensive; never block launch
        # The full seeder failed — still guarantee the priority ethics preload.
        print(f"CFA first-launch seeding degraded: {exc}", file=sys.stderr)
        added = ensure_ethics_deck(col)
        # Leave cfa_seeded unset so the main deck is retried on a later launch,
        # but confirm the ethics preload that did succeed.
        if added:
            tooltip(f"CFA Ethics deck loaded: +{added} ethics pairs.", parent=mw)
