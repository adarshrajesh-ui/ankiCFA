#!/bin/bash
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# ankiCFA launcher — runs the CFA Level II study app on a clean machine from the
# pre-built wheels in ./wheels, using a self-contained virtual environment.
#
# Prerequisite: Apple-Silicon (arm64) macOS 12+ with Python 3.10+ available as
# `python3` (e.g. `brew install python@3.12`). The bundled wheels are arm64-only;
# on any other platform build & launch from source with `just run` instead
# (the guaranteed fallback — see docs/cfa/PACKAGING.md).
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

# --- Interpreter validation --------------------------------------------------
# The bundled wheels are Apple-Silicon (arm64) macOS, Python 3.10+ (cp310-abi3).
# Validate up front and fail with an actionable message instead of a confusing
# pip/venv error later.
if ! command -v python3 >/dev/null 2>&1; then
  echo "error: 'python3' not found on PATH." >&2
  echo "  Fix: install Python 3.10+ (Apple Silicon), e.g. 'brew install python@3.12'." >&2
  echo "  Or launch from source instead: 'just run' (see docs/cfa/PACKAGING.md)." >&2
  exit 1
fi

# Read version+arch+platform from the interpreter that will build the venv; this
# catches an x86_64 (Rosetta/anaconda) python on an Apple-Silicon machine, which
# cannot install the arm64 wheels.
PY_INFO="$(python3 -c 'import sys, platform; print(sys.version_info.major, sys.version_info.minor, platform.machine(), sys.platform)')"
read -r PY_MAJOR PY_MINOR PY_ARCH PY_PLATFORM <<< "$PY_INFO"

if [ "$PY_PLATFORM" != "darwin" ] || [ "$PY_ARCH" != "arm64" ]; then
  echo "error: the bundled ankiCFA wheels are Apple-Silicon macOS only (arm64/darwin)." >&2
  echo "  detected: platform='$PY_PLATFORM' arch='$PY_ARCH'." >&2
  echo "  Fix: use a native arm64 python3 on an Apple-Silicon Mac, or build & launch" >&2
  echo "       from source with 'just run' (see docs/cfa/PACKAGING.md) — always works." >&2
  exit 1
fi

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo "error: Python 3.10+ required (detected ${PY_MAJOR}.${PY_MINOR})." >&2
  echo "  Fix: 'brew install python@3.12' (or use pyenv), then re-run." >&2
  exit 1
fi
echo "Interpreter OK: Python ${PY_MAJOR}.${PY_MINOR} (${PY_ARCH}/${PY_PLATFORM})."

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
# aqt has no runnable __main__ (so `python -m aqt` fails). The aqt wheel installs
# a console script `anki = aqt:run`; use it, falling back to calling aqt.run()
# directly if the script is unavailable.
if [ -x "$VENV/bin/anki" ]; then
  exec "$VENV/bin/anki" "$@"
else
  exec "$VENV/bin/python" -c "import aqt; aqt.run()" "$@"
fi
