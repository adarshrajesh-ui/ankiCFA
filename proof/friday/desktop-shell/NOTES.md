# friday/desktop-shell — native-CFA desktop shell

Workstream: make the DESKTOP app read as a native CFA product end-to-end.
Branch: `friday/desktop-shell` (off origin/main @ 6ef32ec8c).

Offline test harness (env has no system deps; use the project pyenv):
`QT_QPA_PLATFORM=offscreen PYTHONPATH="out/pylib:pylib:qt:out/qt" out/pyenv/bin/python -m pytest ...`
Gate recipe: `just cfa-desktop-shell-test`.

Adaptations (Phase 0 not yet landed by orchestrator at start):
- Scores consumed via the existing Python `anki.cfa.*` API (memory/performance/
  readiness/bayesian). These become thin RPC wrappers later, so the mediasrv
  payload stays forward-compatible.
- AI toggle reads/writes col.conf keys `cfa_ai_enabled` / `cfa_ai_grading_enabled`
  / `cfa_ai_tabfill_enabled` directly (contract-compatible).

---

## Increment 1 — CFA branding (app name, window title, window icon)

- Files (my scope only):
  - `qt/aqt/__init__.py` — startup banner `Starting ankiCFA`; `setApplicationName("ankiCFA")`;
    `setDesktopFileName("ankicfa")`; `app.setWindowIcon(QIcon("icons:cfa.png"))`.
  - `qt/aqt/main.py` — new `window_title()` -> `"ankiCFA - {profile}"` used at loadProfile
    and updateTitleBar; `self.setWindowIcon(QIcon("icons:cfa.png"))` after `setupUi`.
  - `qt/aqt/forms/main.ui` — default title `ankiCFA`; window icon `:/icons/cfa.png`.
  - `qt/aqt/data/qt/icons/cfa.png` — new 256×256 CFA window icon (navy tile, "CFA"
    monogram, orange accent rule); auto-globbed into icons.qrc by the build.
  - `justfile` — `just cfa-desktop-shell-test` gate.
  - `qt/tests/test_cfa_branding.py` — 4 tests.
- Evidence:
  - before (stock strings): `item1-branding-before.txt`
  - before (RED test run, edits stashed): `item1-branding-before-test.txt` (4 failed)
  - after (GREEN test run): `item1-branding-after-test.txt` (4 passed)
  - after (icon asset): `qt/aqt/data/qt/icons/cfa.png`
  - after (labeled before/after title-bar render): `item1-branding-after-titlebar-render.png`
  - build green + generated form branded: `item1-build-green.txt`
- Build: `./ninja pylib qt` green; generated `out/qt/_aqt/forms/main_qt6.py` now emits
  `setWindowTitle("ankiCFA")` + `QPixmap("icons:cfa.png")`; `icons.qrc` includes `cfa.png`.
- Tests: `just cfa-desktop-shell-test` (4 passed). RED proven by stashing only my
  tracked source edits.
- SHA: (this commit)
- PR: (opened after push)
- Cross-scope handoffs: none. (Noted: `justfile` and `qt/tests/` are shared across
  concurrent workers; committed only my own hunk/file.)
