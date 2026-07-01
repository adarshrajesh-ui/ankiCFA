#!/usr/bin/env bash
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# Desktop build gate for the Anki fork (macOS, and Linux with the same
# toolchain). Verifies, in order:
#   (a) the fork builds from source           (just build)
#   (b) the full pre-existing test suite passes (just test: rust + py + ts)
#   (c) our new mastery-query tests pass       (3 Rust + 1 Python)
#   (d) the built app entry point exists       (out/pyenv/bin/anki + _rsbridge)
#
# Exits 0 only if every step passes, and prints a PASS/FAIL summary.
# Written for portable bash (works with the bash 3.2 shipped on macOS).
#
# Usage: bash scripts/verify_desktop.sh

set -u

# Move to the repository root (this script lives in scripts/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Newline-separated "PASS|label" / "FAIL|label" lines, filled in below.
SUMMARY=""
OVERALL=0

run_step() {
    local label="$1"
    shift
    echo ""
    echo "==============================================================="
    echo ">>> ${label}"
    echo "    \$ $*"
    echo "==============================================================="
    if "$@"; then
        SUMMARY="${SUMMARY}PASS|${label}
"
    else
        SUMMARY="${SUMMARY}FAIL|${label}
"
        OVERALL=1
    fi
}

assert_built_app() {
    local ok=0
    if [ -x "out/pyenv/bin/anki" ]; then
        echo "found launcher: out/pyenv/bin/anki"
    else
        echo "MISSING: out/pyenv/bin/anki"
        ok=1
    fi
    local rsbridge
    rsbridge="$(find out/pylib/anki -name '_rsbridge*.so' -print -quit 2>/dev/null || true)"
    if [ -n "${rsbridge}" ]; then
        echo "found Rust extension: ${rsbridge}"
    else
        echo "MISSING: out/pylib/anki/_rsbridge*.so"
        ok=1
    fi
    return "${ok}"
}

# The qt installer tests need the Briefcase app-template submodules checked out.
# Initialise them if missing so the full suite can run; a no-op once present.
# Skipped (with a warning) if the clone fails, e.g. no network.
ensure_submodules() {
    if [ -f "qt/installer/mac-template/cookiecutter.json" ]; then
        echo "briefcase templates already present"
        return 0
    fi
    echo "initialising briefcase template submodules..."
    git submodule update --init \
        qt/installer/mac-template qt/installer/windows-template \
        || echo "WARNING: submodule init failed (offline?); installer tests may fail"
}
ensure_submodules

# (a) Build from source.
run_step "build (just build)" just build

# (b) Full pre-existing test suite (Rust + Python + TypeScript).
run_step "full test suite (just test)" just test

# (c) Our new mastery-query tests, run explicitly so their result is visible
#     even though (b) already exercises them.
run_step "rust mastery tests" \
    cargo test -p anki stats::mastery -- --nocapture
run_step "python mastery test" \
    env PYTHONPATH=out/pylib ANKI_TEST_MODE=1 \
    out/pyenv/bin/pytest -p no:cacheprovider -v pylib/tests/test_mastery.py

# (d) Built app entry point exists.
run_step "built app present" assert_built_app

# Summary.
echo ""
echo "==============================================================="
echo "VERIFY DESKTOP SUMMARY"
echo "==============================================================="
printf '%s' "${SUMMARY}" | while IFS='|' read -r status label; do
    [ -n "${label}" ] && printf '  [%s] %s\n' "${status}" "${label}"
done
echo "---------------------------------------------------------------"
if [ "${OVERALL}" -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
echo "==============================================================="
exit "${OVERALL}"
