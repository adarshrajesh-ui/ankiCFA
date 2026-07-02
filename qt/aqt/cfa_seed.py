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


def maybe_seed(mw: AnkiQt) -> None:
    """Seed the CFA decks on first load of a fresh collection.

    Safe and idempotent: a no-op once ``cfa_seeded`` is set, and even if forced
    the underlying seeder skips decks that already hold cards. Any failure is
    swallowed (logged) so a seeding hiccup never blocks opening the profile.
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

    try:
        import seed_collection

        summary = seed_collection.seed_collection(col, repo_root=repo)
        col.set_config(SEEDED_CONFIG_KEY, True)
        if summary.get("main_seeded") or summary.get("ethics_seeded"):
            from aqt.utils import tooltip

            tooltip(
                "CFA decks loaded: "
                f"+{summary.get('notes_added', 0)} CFA Level II cards, "
                f"+{summary.get('ethics_added', 0)} ethics pairs.",
                parent=mw,
            )
    except Exception as exc:  # pragma: no cover - defensive; never block launch
        print(f"CFA first-launch seeding skipped: {exc}", file=sys.stderr)
