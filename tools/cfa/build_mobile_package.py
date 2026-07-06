# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork — Feature F7: build the mobile CFA study package.

Bundles the two CFA study decks the phone should ship with into ONE importable
Anki package (``.apkg``):

* ``CFA Level II``      — the authored deck (cfa/deck/*.jsonl)
* ``CFA::Ethics Pairs`` — the two-vignette minimal-pairs ethics FLAGSHIP (with its
                          multi-span tap/drag highlight card template + shared
                          partial-credit grader JS)

This bundles the SAME single ethics flagship the desktop first-launch seeder
seeds (``tools/cfa/seed_collection.py`` → ``import_pairs``), so desktop and mobile
ship the one, identical ethics deck. (Previously the phone bundled the retired
one-passage ethics deck while desktop seeded pairs — that duplication is retired
here; see proof/friday/ethics INC3/INC4.)

The whole collection is exported (``did = None``) so both decks, their
note-types, and the ethics card's HTML/CSS/JS templates travel together. The
resulting ``.apkg`` is what AnkiDroid auto-imports as an app asset on first
launch (see F7 on-device wiring), and is also what we push + import onto the
emulator to prove the ethics card renders and multi-span highlight works on
device.

The exam config is persisted into the scratch collection before export. The
package also carries a small ``CFA::_Internal`` manifest note so phone/fork
consumers can see which CFA decks, templates, and phone-supported behaviours are
present even on import paths that do not preserve arbitrary ``col.conf``.

No AI — pure deck authoring, exactly mirroring the desktop first-launch seeder.
"""

from __future__ import annotations

import argparse
import os
import sys


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


REPO = _repo_root()
PACKAGE_MANIFEST_KEY = "cfa.mobile.package_manifest"


def _ensure_import_paths() -> None:
    for rel in ("tools/cfa", "cfa/ethics_pairs", "pylib", "out/pylib"):
        full = os.path.join(REPO, rel)
        if os.path.isdir(full) and full not in sys.path:
            sys.path.insert(0, full)


def build_package(col_path: str, apkg_path: str) -> dict:
    """Seed a collection with both CFA decks and export it to ``apkg_path``.

    Bundles the authored ``CFA Level II`` deck plus the ``CFA::Ethics Pairs``
    minimal-pairs flagship (via ``import_pairs``), exactly mirroring the desktop
    first-launch seeder so both platforms ship the one identical ethics deck.

    Returns a summary dict. ``col_path`` must not already exist (a fresh build).
    """
    _ensure_import_paths()

    import build_cfa_deck  # tools/cfa
    import import_pairs as ethics_pairs  # cfa/ethics_pairs

    from anki.cfa_internal_state import upsert_cfa_state_record
    from anki.collection import Collection
    from anki.exporting import AnkiPackageExporter

    col = Collection(col_path)
    try:
        deck_stats = build_cfa_deck.add_deck_notes(col)
        pairs = ethics_pairs.load_pairs()
        ethics_stats = ethics_pairs.import_pairs(col, pairs)
        upsert_cfa_state_record(
            col,
            PACKAGE_MANIFEST_KEY,
            {
                "package": "cfa-mobile-apkg",
                "version": 1,
                "decks": {
                    "main": build_cfa_deck.MAIN_DECK_NAME,
                    "ethics": ethics_stats["deck"],
                },
                "notetypes": {
                    "main": "CFA Knowledge",
                    "ethics": ethics_stats["notetype"],
                },
                "phoneSupported": [
                    "authored-cfa-level-ii-cards",
                    "phone-friendly-cfa-study-card-template",
                    "minimal-pair-ethics-touch-highlighting",
                    "deterministic-ethics-grading",
                    "named-source-footers",
                    "content-type-tags",
                ],
                "requiresNativeClient": [
                    "cfa-home-shell",
                    "cfa-study-shell",
                    "cfa-concept-map-shell",
                    "cfa-readiness-shell",
                    "first-launch-apkg-auto-import",
                    "shared-rust-cfa-score-rpcs",
                ],
                "limits": [
                    "this repo exports phone content/templates; native AnkiDroid UI lives outside this repo",
                    "collection config such as cfa_exam_config may need normal sync if an importer does not preserve col.conf",
                ],
            },
        )

        # Export the WHOLE collection (did=None) so both decks + their
        # note-types + the ethics card templates + internal manifest travel
        # together.
        exporter = AnkiPackageExporter(col)
        exporter.did = None
        exporter.includeMedia = True
        exporter.exportInto(apkg_path)

        return {
            "apkg": apkg_path,
            "cfa_notes": deck_stats["notes_added"],
            "topics": len(deck_stats["topic_weights"]),
            "ethics_notes": ethics_stats["total"],
            "ethics_deck": ethics_stats["deck"],
            "ethics_notetype": ethics_stats["notetype"],
            "manifest_key": PACKAGE_MANIFEST_KEY,
        }
    finally:
        col.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the CFA mobile study .apkg.")
    ap.add_argument(
        "--col",
        default=os.path.join("/tmp", "cfa_mobile_build.anki2"),
        help="Scratch collection path to build into (created fresh; deleted after).",
    )
    ap.add_argument(
        "--apkg",
        required=True,
        help="Output .apkg path (both decks, whole collection).",
    )
    args = ap.parse_args(argv)

    # Fresh build: clear any prior scratch collection + media dir.
    for p in (args.col, args.col + "-wal", args.col + "-shm"):
        if os.path.exists(p):
            os.remove(p)
    media = os.path.splitext(args.col)[0] + ".media"
    if os.path.isdir(media):
        import shutil

        shutil.rmtree(media)

    summary = build_package(args.col, args.apkg)
    size = os.path.getsize(args.apkg)
    print(
        f"Built {summary['apkg']} ({size} bytes): "
        f"{summary['cfa_notes']} CFA notes / {summary['topics']} topics + "
        f"{summary['ethics_notes']} ethics minimal-pairs ({summary['ethics_deck']})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
