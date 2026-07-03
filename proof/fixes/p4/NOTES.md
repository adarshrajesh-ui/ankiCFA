# ankiCFA — P4: Engineering-Quality Gaps & Submission Proof — NOTES

Owner: **P4** workstream. Every increment is additive, evidence-first, and gated via `no-mistakes`.

Scope owned: `.env` / `.env.example` / `.gitignore`; mypy/type fixes in non-Qt CFA files
(`tools/cfa/sync_roundtrip.py`, `pylib/anki/cfa_sync.py`, mypy path config); the aqt test
PYTHONPATH wiring; `cfa/ai/*` and `cfa/ethics_pairs/eval_*` with-key proof; `proof/` & `demo/`
artifacts.

Not owned (do **not** edit): `qt/aqt/cfa.py` & `pylib/anki/cfa.py` (P1), `docs/` (P3),
the AnkiDroid repo (P2). Residual mypy errors in P1 files are flagged here, not fixed.

---

## Item 1 — Key hygiene (SECURITY)

- Branch: `p4/01-key-hygiene` (off `origin/main` @ `557a7cc82`)
- Commit SHA: _recorded via `git log` on the branch_
- Gate (no-mistakes): _outcome + PR link appended after the run_

What was found / done (additive):

- Verified the real `OPENAI_API_KEY` lives ONLY in the gitignored, untracked `.env`.
  `git check-ignore .env` passes; `.env` is neither tracked nor staged.
- `.env.example` holds the placeholder `OPENAI_API_KEY=sk-your-key-here` (no real key).
- Strict grep `sk-(proj-)?[A-Za-z0-9_-]{20,}` over tracked files returns only TWO matches,
  both the intentional fake fixture `sk-should-never-appear-in-prompt` in
  `cfa/ethics_pairs/tests/test_ai_grading.py` — the redaction test
  `test_prompt_includes_evidence_and_never_the_key`, which proves the real key is never sent
  to the LLM. Excluding that test file → **ZERO** matches, proving no real key is tracked.
  The security test was intentionally left intact (documented, not weakened).
- Hardening: extended `.gitignore` to also ignore `.env.*` variants (e.g. `.env.local`,
  `.env.withkey.bak`) while keeping `.env.example` tracked — this prevents accidentally
  committing key-bearing backups, notably the `.env.withkey.bak` the Item 4 with-key proof
  creates when it exercises the AI-off fallback.

Evidence:

- Before: `proof/fixes/p4/1-keyhygiene-before.txt`
- After:  `proof/fixes/p4/1-keyhygiene-after.txt`

Verify (AI-off unaffected): no application code changed — only `.gitignore` + proof files.

<!-- Subsequent items (2–5) append their entries below. -->

---

## Item 2 — mypy debt

- Branch: `p4/02-mypy`
- Commit SHA: `200c0a22e7bda331f292d38d0d3040ee96d69545`
- Evidence — Before: `proof/fixes/p4/2-mypy-before.txt`
- Evidence — After:  `proof/fixes/p4/2-mypy-after.txt`
- Build: cold `just build` in the fresh worktree succeeded (needed for the generated
  stubs under `out/pylib/anki` + `out/qt/_aqt` that mypy consumes).

Mypy outcome (`check:mypy` = `mypy pylib qt/aqt qt/tools out/pylib/anki out/qt/_aqt python tools`):

- **21 errors (13 files) → 3 errors (1 file).**
- **Owned scope: 0 errors.** All 16 import-not-found cleared; the 2 genuine owned
  errors in `tools/cfa/sync_roundtrip.py` fixed; `pylib/anki/cfa_sync.py` was already
  clean (verified — no changes invented there); `cfa/**` (followed via
  `cfa.ai.llm_client`) clean.

Reality vs. the assumed diagnosis: the import-not-found errors were **not** `cfa.*`
package imports but **bare-name** sibling imports (`import ethics_scoring`, `import
build_cfa_deck`, …) resolved at RUNTIME via `sys.path.insert(0, …)` hacks, plus the
optional third-party `openai`. The genuine `cfa.*` package imports (`cfa.ai.llm_client`)
already resolved via mypy's implicit cwd base.

What changed (config + type-annotation only; no runtime behavior change):

- `.mypy.ini`: `mypy_path += .` (repo root) — makes `cfa.ai.llm_client` resolve
  explicitly on the search path (mirrors the recipes' runtime `PYTHONPATH=…:.`).
- `.mypy.ini`: targeted per-module `ignore_missing_imports` for `openai` /`openai.*`
  (optional SDK, try/except ImportError, not in the type-check venv — matches
  `[mypy-bs4]`) and for the bare first-party CFA modules `ethics_scoring`,
  `ai_grading`, `passages`, `import_pairs`, `build_cfa_deck`, `seed_collection`.
  Rooting their dirs was rejected empirically: adding `tools/cfa` triggers a fatal
  `Source file found twice under different module names` (it is already checked as
  the `tools.cfa.*` package), and rooting `cfa/ethics_pairs` widens the target's
  scope, pulling the out-of-scope, non-owned proof script
  `tools/cfa/render_f2_ai_grade.py` into the graph and surfacing 5 pre-existing
  dict-typing errors there. The targeted ignores clear the noise without blanket
  silencing and without changing the check's designed folder scope.
- `tools/cfa/sync_roundtrip.py` (OWNED): `_add_card -> CardId`,
  `_review(cid: CardId, ease: Literal[1, 2, 3, 4])`, + imports `Literal`/`CardId`
  (`from __future__ import annotations` in effect → annotations never evaluated;
  `CardId` is a `NewType == int`).

P1-file errors flagged (in `qt/aqt/cfa.py` — NOT fixed here; P1 owns that file;
pre-existing, present in the BEFORE run too):

- `qt/aqt/cfa.py:135: [arg-type]` `order=<int>` passed to `SearchTerm(order=…)`, whose
  protobuf field expects the enum `ValueType`.
- `qt/aqt/cfa.py:386: [assignment]` `for col in range(1, 5):` rebinds `col`, which is
  the `Collection` earlier in the function (loop-variable shadowing). Fix: rename the
  loop index.
- `qt/aqt/cfa.py:387: [call-overload]` `setSectionResizeMode(col, …)` — a knock-on of
  the `:386` shadowing; resolved once the loop variable is renamed.

Verify (AI-off unaffected): only `.mypy.ini` (config) and three type annotations in a
demo/proof driver changed. `cfa/ai/llm_client.py` is untouched and its `openai` import
is still guarded by try/except ImportError; `ruff check tools/cfa/sync_roundtrip.py`
passes.

Gate: DEFERRED — `no-mistakes` intentionally NOT run for this item.

---

## Item 3 — aqt test wiring (aqt TEST HARNESS WIRING)

- Branch: `p4/03-aqt` (stacked on `p4/02-mypy`, which contains items 1 + 2)
- Commit SHA: `4af70d0f89dc8d540b3faaac3a2d66c58247f883`
- Evidence — Before: `proof/fixes/p4/3-aqt-before.txt`
- Evidence — After:  `proof/fixes/p4/3-aqt-after.txt`

The bug: the global gate target `check:pytest:aqt` (defined in
`build/configure/src/aqt.rs`) ran pytest with
`PYTHONPATH=pylib:$builddir/pylib:$builddir/qt:$builddir/qt/tools` — which OMITS the
repo root (`$builddir` = `out`). The gate invokes the `pytest` CONSOLE SCRIPT
(`out/pyenv/bin/pytest`) which, unlike `python -m pytest`, does NOT add the CWD to
`sys.path`. So the AI-off default-client lazy import at `qt/aqt/cfa_tab_fill.py:157`
(`from cfa.ai.llm_client import complete`) raised `ModuleNotFoundError: No module named
'cfa'`, failing `test_fill_note_back_ai_off_leaves_note_untouched`. It passed only under
`just cfa-tab-fill-test`, whose PYTHONPATH ends with the repo root `.`.

Reproduction note: the item's literal `python -m pytest …` command MASKS the bug (the
`-m` form prepends the CWD/repo root to `sys.path`, so it reports 18 passed). The
faithful BEFORE repro therefore uses the console-script pytest, exactly like the gate —
see `3-aqt-before.txt`.

The fix (test wiring / build-config only — NO product code touched):

- `build/configure/src/aqt.rs`, fn `check_python`, target `check:pytest:aqt`: appended
  `"."` (repo root) to the `python_path` array; existing entries unchanged and not
  reordered:

      python_path: &[
          "pylib",
          "$builddir/pylib",
          "$builddir/qt",
          "$builddir/qt/tools",
          // repo root, so first-party `cfa.*` packages resolve under the gate
          ".",
      ],

  This mirrors the working `just cfa-tab-fill-test` recipe (PYTHONPATH ends with `.`).

Gate outcome (REAL regenerated global gate via `just test-py`):

- Regeneration was AUTOMATIC: ninja recompiled `build:configure_bin` and re-ran
  `build:configure`; the generated `out/build.ninja` now shows
  `pythonpath = pylib:$builddir/pylib:$builddir/qt:$builddir/qt/tools:.` (repo root
  present; pytest still the console script `$builddir/pyenv/bin/pytest`).
- `check:pytest:aqt` → `qt/tests/test_cfa_tab_fill.py` = 18/18 PASS, including the
  previously-failing `test_fill_note_back_ai_off_leaves_note_untouched`.
- Full aqt suite delta (same command, only the repo-root entry differs):
  BEFORE (old path) 3 failed / 119 passed → AFTER (regenerated gate) 2 failed /
  120 passed. Exactly +1 fixed, ZERO regressions. Sibling suites unaffected:
  `check:pytest:pylib` 173 passed, `check:pytest:tools` 4 passed.
- The remaining 2 failures (`test_installer.py::test_compile_fails_loudly`,
  `::test_build_and_package`) are PRE-EXISTING / environmental — Briefcase cannot clone
  the mac app template ("Unable to clone application template … mac-template … correct?").
  Proven PYTHONPATH-INDEPENDENT: they fail identically under the OLD gate path, so this
  fix neither causes nor affects them. They live in `qt/tests` (so technically inside
  `check:pytest:aqt`) but are upstream/env issues, not ours to fix.

Verify (AI-off unaffected): build-config only; `just cfa-tab-fill-test` still passes
(18 passed) after the change; `qt/aqt/cfa_tab_fill.py` and `cfa/ai/llm_client.py` are
untouched.

Gate: DEFERRED — `no-mistakes` intentionally NOT run for this item.
