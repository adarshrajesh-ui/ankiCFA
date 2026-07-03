# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""item4 repro — the F1 one-passage flagship deck "CFA::Ethics Passages" has no
desktop CFA-menu entry, so it is unreachable on desktop.

Prints per-check "VERDICT: OK/BUG". Run it twice — once with the source fix
stashed (reproduces the gap) and once with the fix applied (all OK):

    QT_QPA_PLATFORM=offscreen \
    PYTHONPATH="out/pylib:pylib:qt:out/qt:cfa/ethics_pairs" \
    out/pyenv/bin/python proof/fixes/p1/item4_repro.py
"""

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMenuBar, QWidget

from anki.collection import Collection
from aqt import cfa, cfa_seed

PASSAGES_DECK = "CFA::Ethics Passages"
ONE_PASSAGE_LABEL = "Study Ethics (One-Passage)"

_APP = QApplication.instance() or QApplication(["repro"])


def _menu_labels() -> list[str]:
    mw = QWidget()
    mw.form = SimpleNamespace(menubar=QMenuBar())  # type: ignore[attr-defined]
    cfa.setup_menu(mw)  # type: ignore[arg-type]
    return [a.text() for a in mw._cfa_menu.actions()]  # type: ignore[attr-defined]


def main() -> int:
    bugs = 0

    # Check 1 — the desktop CFA menu must expose a one-passage study action.
    labels = _menu_labels()
    print("CFA menu actions:", labels)
    if ONE_PASSAGE_LABEL in labels:
        print(f"  VERDICT: OK — '{ONE_PASSAGE_LABEL}' present")
    else:
        bugs += 1
        print(
            f"  VERDICT: BUG — '{ONE_PASSAGE_LABEL}' MISSING "
            "(passages deck unreachable on desktop)"
        )

    # Check 2 — an on-demand seeder helper for the passages deck must exist.
    if hasattr(cfa_seed, "ensure_ethics_passages_deck"):
        print("cfa_seed.ensure_ethics_passages_deck: present\n  VERDICT: OK")
    else:
        bugs += 1
        print(
            "cfa_seed.ensure_ethics_passages_deck: MISSING\n"
            "  VERDICT: BUG — no on-demand seeder for the passages deck"
        )

    # Check 3 — a study handler that enters review on the deck must exist.
    if hasattr(cfa, "study_ethics_passages"):
        print("cfa.study_ethics_passages: present\n  VERDICT: OK")
    else:
        bugs += 1
        print(
            "cfa.study_ethics_passages: MISSING\n"
            "  VERDICT: BUG — no handler to enter review on the passages deck"
        )

    # Check 4 — on a fresh profile the passages deck is empty/unreachable; the
    # desktop action (if any) must seed it on demand and enter review with NO
    # false "not available in this build" modal.
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    col = Collection(path)
    try:
        did = col.decks.id_for_name(PASSAGES_DECK)
        n0 = col.decks.card_count(did, include_subdecks=True) if did is not None else 0
        print(f"fresh profile: '{PASSAGES_DECK}' cards = {n0}")
        study = getattr(cfa, "study_ethics_passages", None)
        if study is None:
            bugs += 1
            print("  VERDICT: BUG — no desktop entry point can reach the passages deck")
        else:
            states: list[str] = []
            mw = SimpleNamespace(
                col=col,
                states=states,
                reset=lambda: None,
                moveToState=lambda s: states.append(s),
            )
            cfa.showInfo = lambda *a, **k: states.append("INFO")  # type: ignore[assignment]
            cfa.showWarning = lambda *a, **k: states.append("WARN")  # type: ignore[assignment]
            cfa.tooltip = lambda *a, **k: None  # type: ignore[assignment]
            study(mw)
            did = col.decks.id_for_name(PASSAGES_DECK)
            n1 = (
                col.decks.card_count(did, include_subdecks=True)
                if did is not None
                else 0
            )
            print(f"after study action: cards = {n1}, states = {states}")
            if n1 == 30 and "review" in states and "INFO" not in states:
                print(
                    "  VERDICT: OK — seeded on demand + entered review, no false modal"
                )
            else:
                bugs += 1
                print("  VERDICT: BUG — did not seed + enter review cleanly")
    finally:
        col.close()

    print()
    print(
        "ITEM4 REPRO:", "ALL OK (fixed)" if bugs == 0 else f"{bugs} BUG(S) REPRODUCED"
    )
    return 1 if bugs else 0


if __name__ == "__main__":
    raise SystemExit(main())
