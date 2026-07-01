#!/usr/bin/env bash
# Verify the honest measurement layer (speedrun_scoring).
#
# 1. runs pytest over models, give-up rule, coverage map, calibration, leakage
# 2. runs a headless eval that prints calibration + paraphrase-gap on fixtures
# Exits 0 only if everything passes.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Pick an interpreter that has pytest (dev machines vary).
pick_python() {
  for cand in "${SPEEDRUN_PYTHON:-}" python3 python; do
    [ -z "$cand" ] && continue
    if "$cand" -c "import pytest" >/dev/null 2>&1; then
      echo "$cand"
      return 0
    fi
  done
  # anaconda fallback commonly present on dev machines
  for cand in "$HOME/anaconda3/bin/python3" "$HOME/miniconda3/bin/python3"; do
    if [ -x "$cand" ] && "$cand" -c "import pytest" >/dev/null 2>&1; then
      echo "$cand"
      return 0
    fi
  done
  return 1
}

PY="$(pick_python)" || {
  echo "ERROR: no Python interpreter with pytest found." >&2
  echo "Install pytest (pip install pytest) or set SPEEDRUN_PYTHON." >&2
  exit 1
}
echo "Using interpreter: $PY"

export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "== pytest =="
"$PY" -m pytest speedrun_scoring/tests -q

echo
echo "== headless eval =="
"$PY" -m speedrun_scoring.eval

echo
echo "verify_scoring: ALL PASSED"
