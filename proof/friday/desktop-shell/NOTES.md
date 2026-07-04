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
- SHA: `22013a473` (on friday/desktop-shell, in the isolated worktree)
- PR: https://github.com/adarshrajesh-ui/ankiCFA/pull/24
- Cross-scope handoffs: see `HANDOFF.md` — isolation move + a friday/ethics
  concurrency incident I cleaned up. `justfile`/`qt/tests/` are shared across
  concurrent workers; I commit only my own hunk/files.

---

## Increment 2 — CFA Home is the native landing screen

The app now opens into a native CFA dashboard instead of the stock Anki deck
list. Deck list stays reachable (toolbar "Decks", the Home "Browse decks" CTA,
`d` shortcut).

- Files (my scope only):
  - `proto/anki/frontend.proto` — `rpc GetCfaHomeView(generic.Empty) returns (generic.Json)`.
  - `qt/aqt/mediasrv.py` — `_cfa_home_payload` (reuses `_cfa_exam_readiness_payload`
    for score parity + adds examDate/daysToExam/aiEnabled) + `get_cfa_home_view`
    handler; registered in `post_handler_list`; `cfa-home` added to
    `is_sveltekit_page`; `/_anki/getCfaHomeView` whitelisted (main webview, like
    congratsInfo).
  - `qt/aqt/webview.py` — `AnkiWebViewKind.CFA_HOME` + api-access.
  - `qt/aqt/main.py` — `cfaHome` state, `setupCfaHome`, `_cfaHomeState` (defensive),
    and the landing change: profile load `moveToState("cfaHome")`.
  - `qt/aqt/cfa_home.py` (new) — `CfaHome` controller: loads the SvelteKit page in
    the main webview + routes CTA bridgeCommands to the existing
    `cfa.study_*/show_*` entry points (+ `open_ai_settings` placeholder for INC5).
  - `ts/lib/cfa/types.ts` + `index.ts` — `CfaHomePayload`.
  - `ts/lib/cfa/pages/CfaHomePage.svelte` + `home.ts` — the dashboard (design-system
    Hero/StatCard/PageHeading; 3 honest scores; exam countdown; CTA grid; AI chip).
  - `ts/routes/cfa-home/+page.ts` + `+page.svelte` — the route (getCfaHomeView -> page).
  - `qt/tests/test_cfa_home.py` (6 tests).
- Data path: consumes the Python `anki.cfa.*` scores (RPC-wrapper-ready). CTAs use
  `bridgeCommand` (proven by the congrats page) — no cross-thread Qt from mediasrv.
- Evidence:
  - before (feature absent at base 6ef32ec8c): `item2-home-before.txt`
  - after (REAL render via the live mediasrv + seeded deck): `item2-home-after.png`
    — 151 days to exam, "likely pass (p=0.97)", Memory 82–100% / Performance
    67–84% / Readiness 53–100%, 8/8 topics, 536 graded reviews, 5 CTAs, AI Off.
- Build: `./ninja pylib qt` green (proto regen -> `getCfaHomeView` in @generated/backend
  + cfa-home route bundled). `svelte-check`: 0 errors / 0 warnings (1286 files).
- Tests: `just cfa-desktop-shell-test` -> 10 passed (branding 4 + home 6).
- SHA: (this commit)  ·  PR: #24

---

## Increment 3 — Toolbar + menu reframe

Top bar and CFA menu read as a CFA product.

- Files (my scope only):
  - `qt/aqt/toolbar.py` — `_centerLinks` now Home / Study / Ethics / Readiness
    (+ Sync kept last, ids intact); added `_cfa{Home,Study,Ethics,Readiness}LinkHandler`
    delegating to `moveToState("cfaHome")` / `cfa.study_by_exam_priority` /
    `cfa.study_ethics_pairs` / `cfa.show_exam_readiness`. Add/Browse/Stats stay in
    the menu bar.
  - `qt/aqt/cfa.py` — CFA menu: added "CFA Home"; single ethics entry =
    Minimal-Pairs (one-passage menu action retired; `study_ethics_passages`
    function kept for compatibility).
  - `qt/tests/test_cfa_menu.py` (updated) + `qt/tests/test_cfa_toolbar.py` (new).
- Scope check: `friday/ethics` does NOT touch `cfa.py`/`test_cfa_menu.py`
  (verified `git diff 6ef32ec8c friday/ethics`), so no cross-worker conflict.
- Evidence: `item3-toolbar-menu-before.txt` (stock decks/add/browse/stats +
  one-passage) / `item3-toolbar-menu-after.txt` (reframed links + menu labels).
  The restyled toolbar *visual* lands in Increment 4 (design-system chrome).
- Build: `./ninja pylib qt` green. Tests: `just cfa-desktop-shell-test` → 19 passed
  (branding 4 + home 6 + menu 5 + toolbar 4).
- SHA: (this commit)  ·  PR: #24

---

## Increment 4 — CFA design system re-skins the stock chrome

The remaining stock surfaces (top toolbar + deck list) now carry the CFA palette
+ type, so no screen reads as plain Anki.

- Files (my scope only):
  - `qt/aqt/cfa_chrome.py` (new) — builds CFA CSS from the parity-locked
    `cfa_style.TOKENS` and installs it via public gui_hooks:
    `webview_will_set_content` re-skins the `TopToolbar` (navy links, orange
    hover) and the `DeckBrowser` (CFA page tint + type + an "ankiCFA · Level II /
    Your decks" banner); `deck_browser_will_render_content` adds a quiet CFA
    caption. Idempotent `register()`.
  - `qt/aqt/cfa.py` — call `cfa_chrome.register()` from `setup_menu` (guarded).
  - `qt/tests/test_cfa_chrome.py` (5 tests).
- Approach: additive — no stock render code rewritten, no scss rebuild. Palette
  is byte-parity with the SvelteKit `_tokens.scss` (same source: `cfa_style.TOKENS`).
- Scope check: no `friday/*` worker touches `deckbrowser.py`/`cfa_style.py`.
- Evidence: `item4-chrome-before.txt` (chrome absent at base) + honest before/after
  CSS-composited render `item4-chrome-before-after.png` (real compiled
  toolbar.css/deckbrowser.css + the exact injected CFA CSS).
- Build: `./ninja pylib qt` green. Tests: `just cfa-desktop-shell-test` → 24 passed.
- SHA: (this commit)  ·  PR: #24
