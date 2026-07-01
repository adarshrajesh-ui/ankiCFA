#!/bin/bash
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# ankiCFA launcher — runs the CFA Level II study app on a clean machine from the
# pre-built wheels in ./wheels, using a self-contained virtual environment.
#
# Prerequisite: Python 3.13+ available as `python3` (macOS: `brew install python@3.13`).
#
# Usage:
#   ./launch-ankiCFA.sh            # first run installs into ./anki-venv, then launches
#   ./launch-ankiCFA.sh --build-deck   # also author the CFA Level II deck on first launch

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/anki-venv"
WHEELS="$HERE/wheels"

if [ ! -d "$WHEELS" ] || [ -z "$(ls -A "$WHEELS"/*.whl 2>/dev/null)" ]; then
  echo "error: no wheels found in $WHEELS."
  echo "Build them from the repo with:  just wheels   (output lands in out/wheels/)"
  echo "then copy out/wheels/*.whl into $WHEELS/"
  exit 1
fi

if [ ! -d "$VENV" ]; then
  echo "Creating virtual environment in $VENV ..."
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip wheel >/dev/null
  echo "Installing ankiCFA wheels ..."
  "$VENV/bin/python" -m pip install "$WHEELS"/*.whl
fi

if [ "${1:-}" = "--build-deck" ]; then
  DECK_COL="$HOME/.ankiCFA-deck/cfa.anki2"
  mkdir -p "$(dirname "$DECK_COL")"
  echo "Authoring CFA Level II deck at $DECK_COL ..."
  "$VENV/bin/python" "$HERE/build_cfa_deck.py" --path "$DECK_COL" --apkg "$HERE/CFA-Level-II.apkg" || true
  echo "Import $HERE/CFA-Level-II.apkg from Anki's File > Import."
  shift
fi

echo "Launching ankiCFA ..."
exec "$VENV/bin/python" -m aqt "$@"
