set windows-shell := ["pwsh", "-NoLogo", "-NoProfileLoadTime", "-Command"]

mod release

# Show available commands
default:
    @just --list

# Build the project
build:
    {{ ninja }} pylib qt

# Build and run Anki in development mode
run *args:
    {{ run_script }} {{ args }}

# Build and run Anki in optimized (release) mode
run-optimized *args:
    {{ if os() == "windows" { "$env:RELEASE='1'; .\\run.bat" } else { "RELEASE=1 ./run" } }} {{ args }}

# Watch web sources and rebuild/reload Anki's web stack on change (macOS/Linux)
web-watch:
    ./tools/web-watch

# Rebuild and reload Anki's web stack without restarting (macOS/Linux)
rebuild-web:
    ./tools/rebuild-web

# Build wheels (needed for some platforms)
wheels:
    {{ ninja }} wheels

# Build and run all checks (lint + test) - lets ninja handle dependencies
check:
    {{ ninja }} pylib qt check

# Run all tests (Rust, Python, TypeScript). Pass --coverage to enforce coverage, and --html to include HTML reports.
[arg("coverage", long="coverage", value="--coverage")]
[arg("html", long="html", value="--html")]
test coverage='' html='':
    just {{ if coverage == "--coverage" { "coverage " + html } else { "_test" } }}

# Run coverage for all test stacks. Pass --html to also generate HTML reports.
[arg("html", long="html", value="--html")]
coverage html='':
    just _coverage-rust {{ html }}
    just _coverage-py {{ html }}
    just _coverage-ts {{ html }}

# Run Rust tests. Pass --coverage to enforce Rust coverage, and --html to include an HTML report.
[arg("coverage", long="coverage", value="--coverage")]
[arg("html", long="html", value="--html")]
test-rust coverage='' html='':
    just {{ if coverage == "--coverage" { "_coverage-rust " + html } else { "_test-rust" } }}

# Run Python tests (pylib + qt). Pass --coverage to enforce coverage, and --html to include HTML reports.
[arg("coverage", long="coverage", value="--coverage")]
[arg("html", long="html", value="--html")]
test-py coverage='' html='':
    just {{ if coverage == "--coverage" { "_coverage-py " + html } else { "_test-py" } }}

# Run TypeScript/Svelte Vitest tests. Pass --coverage to enforce coverage, and --html to include an HTML report.
[arg("coverage", long="coverage", value="--coverage")]
[arg("html", long="html", value="--html")]
test-ts coverage='' html='':
    just {{ if coverage == "--coverage" { "_coverage-ts " + html } else { "_test-ts" } }}

# Run Playwright end-to-end tests. Pass --ui to open the interactive UI.
[arg("ui", long="ui", value="--ui")]
test-e2e ui='': _install-playwright-browsers
    {{ ninja }} pyenv ts:generated pylib qt
    {{ playwright_env }} {{ yarn }} test:e2e {{ ui }}

# --- CFA Ethics Minimal-Pairs feature (cfa/ethics_pairs) ---

# Validate the 30-pair bank (pairs.jsonl) without opening a collection
cfa-validate:
    {{ py }} cfa/ethics_pairs/import_pairs.py --dry-run

# Run the Ethics Minimal-Pairs unit tests + jsonl->notes round-trip (builds pylib first)
cfa-test:
    {{ ninja }} pylib
    {{ cfa_env }} {{ py }} -m pytest cfa/ethics_pairs/tests -q

# Validate the authored CFA Level II deck items (cfa/deck/*.jsonl) and run the builder tests
cfa-deck-validate:
    {{ py }} cfa/deck/validate_deck.py

# Run the CFA Level II deck builder + JSONL validator tests (builds pylib first for the round-trip)
cfa-deck-test:
    {{ ninja }} pylib
    {{ cfa_env }} {{ py }} -m pytest tools/cfa/tests -q

# Feature 4: assert the desktop CFA menu exposes its four study actions (needs pylib+_aqt built)
cfa-menu-test:
    {{ ninja }} pylib
    QT_QPA_PLATFORM=offscreen PYTHONPATH="out/pylib:pylib:qt:out/qt" {{ py }} -m pytest qt/tests/test_cfa_menu.py -q

# Build the CFA Level II deck into a collection. Pass col=/path/to/collection.anki2 (must be CLOSED in Anki)
cfa-deck-build col:
    {{ ninja }} pylib
    {{ cfa_env }} {{ py }} tools/cfa/build_cfa_deck.py --path "{{ col }}"

# Import the 30-pair bank into a collection (must be CLOSED in Anki). Pass col=/path/to/collection.anki2
cfa-import col:
    {{ ninja }} pylib
    {{ cfa_env }} {{ py }} cfa/ethics_pairs/import_pairs.py --col "{{ col }}"

# Generate + open the offline discrimination dashboard for a collection (must be CLOSED in Anki)
cfa-dashboard col:
    {{ ninja }} pylib
    {{ cfa_env }} {{ py }} cfa/ethics_pairs/ethics_dashboard.py --col "{{ col }}" --open

# Symlink the in-app dashboard add-on into Anki's addons21 folder (macOS default path)
cfa-install-addon:
    mkdir -p "$HOME/Library/Application Support/Anki2/addons21"
    ln -sfn "$(pwd)/cfa/ethics_pairs" "$HOME/Library/Application Support/Anki2/addons21/cfa_ethics_pairs"
    @echo "Linked add-on into Anki2/addons21 (macOS). See cfa/ethics_pairs/README.md for Linux/Windows paths."

[private]
_test:
    {{ ninja }} check:rust_test check:pytest check:vitest

[private]
_test-rust:
    {{ ninja }} check:rust_test

[private]
_test-py:
    {{ ninja }} check:pytest

[private]
_test-ts:
    {{ ninja }} check:vitest

[private]
_coverage-rust html='':
    {{ if os_family() == "windows" { "tools\\coverage\\coverage-rust" } else { "tools/coverage/coverage-rust" } }} {{ html }}

[private]
_coverage-py html='':
    {{ ninja }} pylib qt
    just _coverage-py-pylib {{ html }}
    just _coverage-py-qt {{ html }}

[private]
_coverage-py-pylib html='':
    {{ if os_family() == "windows" { "tools\\coverage\\coverage-py" } else { "tools/coverage/coverage-py" } }} pylib {{ html }}

[private]
_coverage-py-qt html='':
    {{ if os_family() == "windows" { "tools\\coverage\\coverage-py" } else { "tools/coverage/coverage-py" } }} qt {{ html }}

[private]
_coverage-ts html='':
    {{ ninja }} node_modules ts:generated
    {{ if os_family() == "windows" { "tools\\coverage\\coverage-ts" } else { "tools/coverage/coverage-ts" } }} {{ html }}

[private]
_install-playwright-browsers:
    {{ ninja }} node_modules
    {{ playwright_env }} {{ yarn }} playwright install chromium

# Check formatting (fast, no build needed)
fmt:
    {{ ninja }} check:format

# Fix formatting
fix-fmt:
    {{ ninja }} format

# Run linting and type checking (requires build outputs)
lint:
    {{ ninja }} \
        check:clippy \
        check:mypy \
        check:ruff \
        check:eslint \
        check:svelte \
        check:typescript

# Fix auto-fixable lint issues (ruff + eslint)
fix-lint:
    {{ ninja }} fix:ruff fix:eslint

# Run minilints (copyright, contributors, licenses)
minilints:
    {{ ninja }} check:minilints

# Fix minilints (update licenses.json)
fix-minilints:
    {{ ninja }} fix:minilints

# Sync translation files
ftl-sync:
    {{ ninja }} ftl-sync

# Deprecate translation strings
ftl-deprecate:
    {{ ninja }} ftl-deprecate

# Build documentation site
docs:
    {{ uv }} run --group docs sphinx-build -b html docs out/docs/html
    @echo "Docs built at out/docs/html/index.html"

# Build and serve documentation site
docs-serve:
    {{ uv }} run --group docs sphinx-autobuild docs out/docs/html --host 127.0.0.1 --port 8000

# Build Rust API docs
docs-rust:
    cargo doc --open

# Dispatch CI workflow on a given branch or tag
ci branch:
    gh workflow run ci.yml --ref {{ branch }}

# Run Complexipy in regression-only mode
complexipy-diff:
    {{ ninja }} check:complexipy-diff

# Remove build outputs from out/ (pass keep-env to keep node_modules/pyenv); macOS/Linux
clean *args:
    ./tools/clean {{ args }}

# Helpers to get the right commands for the platform

ninja := if os() == "windows" { "tools\\ninja" } else { "./ninja" }
run_script := if os() == "windows" { ".\\run.bat" } else { "./run" }
playwright_env := if os() == "windows" { "set PLAYWRIGHT_BROWSERS_PATH=out\\playwright-browsers&&" } else { "PLAYWRIGHT_BROWSERS_PATH=out/playwright-browsers" }
yarn := if os() == "windows" { "out\\extracted\\node\\yarn.cmd" } else { "out/extracted/node/bin/yarn" }
uv := env("UV_BINARY", if os() == "windows" { "out\\extracted\\uv\\uv" } else { "out/extracted/uv/uv" })
export UV_PROJECT_ENVIRONMENT := if os() == "windows" { "out\\pyenv" } else { "out/pyenv" }
py := if os() == "windows" { "out\\pyenv\\Scripts\\python.exe" } else { "out/pyenv/bin/python" }
cfa_env := if os() == "windows" { "$env:PYTHONPATH='out\\pylib;cfa\\ethics_pairs'; $env:ANKI_TEST_MODE='1';" } else { "PYTHONPATH=out/pylib:cfa/ethics_pairs ANKI_TEST_MODE=1" }
