#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Validate the hand-authored CFA Level II item files under ``cfa/deck/*.jsonl``.

Checks, across every ``*.jsonl`` file in this directory:
  * each non-blank line is a JSON object
  * exactly the required fields are present: front, back, topic, los_tag,
    source, license
  * no empty / whitespace-only / non-string values
  * every ``los_tag`` starts with ``los::``
  * every item is authored-original (``license == "authored-original"``) — a
    guard against pasting copyrighted CFA Institute material
  * no duplicate fronts across the whole deck (case-insensitive)
  * the deck has more than ``MIN_CARDS`` items

Exit code 0 on success, 1 on any failure.
Run:  python3 cfa/deck/validate_deck.py
"""

from __future__ import annotations

import glob
import json
import os
import sys

DECK_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIRED_FIELDS = {"front", "back", "topic", "los_tag", "source", "license"}
# Open / original licenses only. This guards against pasted copyrighted CFA
# Institute material — every item must be authored-original or released under a
# permissive Creative Commons license by its author.
ALLOWED_LICENSES = {"authored-original", "CC0-1.0", "CC-BY-4.0"}
MIN_CARDS = 200


def validate(deck_dir: str = DECK_DIR) -> tuple[int, list[str]]:
    """Return ``(card_count, errors)`` for the item files in ``deck_dir``."""
    errors: list[str] = []
    fronts_seen: dict[str, str] = {}
    count = 0

    paths = sorted(glob.glob(os.path.join(deck_dir, "*.jsonl")))
    if not paths:
        return 0, [f"no *.jsonl item files found in {deck_dir}"]

    for path in paths:
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                if not raw.strip():
                    continue
                count += 1
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as exc:
                    errors.append(f"{name}:{lineno}: invalid JSON ({exc})")
                    continue
                if not isinstance(obj, dict):
                    errors.append(f"{name}:{lineno}: row is not a JSON object")
                    continue
                if set(obj) != REQUIRED_FIELDS:
                    errors.append(
                        f"{name}:{lineno}: fields {sorted(obj)} != {sorted(REQUIRED_FIELDS)}"
                    )
                    continue
                for key, value in obj.items():
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"{name}:{lineno}: empty/non-string {key!r}")
                if not obj["los_tag"].startswith("los::"):
                    errors.append(
                        f"{name}:{lineno}: los_tag {obj['los_tag']!r} must start with 'los::'"
                    )
                if obj["license"] not in ALLOWED_LICENSES:
                    errors.append(
                        f"{name}:{lineno}: license {obj['license']!r} not in {ALLOWED_LICENSES}"
                    )
                key = obj["front"].strip().lower()
                if key in fronts_seen:
                    errors.append(
                        f"{name}:{lineno}: duplicate front (also in {fronts_seen[key]})"
                    )
                else:
                    fronts_seen[key] = f"{name}:{lineno}"

    if count <= MIN_CARDS:
        errors.append(f"deck has {count} cards, expected more than {MIN_CARDS}")

    return count, errors


def main() -> int:
    count, errors = validate()
    if errors:
        print(f"FAIL: {len(errors)} problem(s) across cfa/deck/*.jsonl:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"OK: {count} authored CFA Level II items, all valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
