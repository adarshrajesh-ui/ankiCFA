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

---

## Item 4 — with-key AI proof (WITH-KEY AI PROOF)

- Branch: `p4/04-withkey` (stacked on `p4/03-aqt`, which contains items 1–3)
- Commit SHA (evidence + render tool): `2522bc7802f74fd140a494907f5f9490b317932f`
- Gate: DEFERRED — `no-mistakes` intentionally NOT run for this item.

Ran the CFA AI features against the REAL `OPENAI_API_KEY` (kept only in the
gitignored, untracked `.env`; never printed, echoed, logged, or committed). Every
commit was preceded by the staged-file scrub
`git diff --cached --name-only | xargs grep -nE 'sk-(proj-)?[A-Za-z0-9_-]{20,}'`,
which came back clean. Preflight `just cfa-ai-smoke` = **9 passed / 0 skipped**,
i.e. `test_with_key_real_tiny_call` made a genuine call and returned `ok=True`.

### Part 1 — F2 eval WITH the real LLM (PASS)

- `just cfa-ethics-eval` (exit 0): `active grader : LLM (semantic)` (NOT the
  deterministic fallback), **grade agreement 0.933 >= threshold 0.80 -> PASS**.
- `--json` confirms `"ran_ai": true`, `"ai_source_count": 30`, `"n": 30`,
  `"grade_agreement": 0.9333` — all 30 attempts graded by the real LLM, no
  fallback mix. Deterministic baseline `0.7333` reported for contrast.
- Evidence: `proof/fixes/p4/f2-withkey-eval.txt`, `proof/fixes/p4/f2-withkey-eval.json`.

### Part 2 — F3 tab-to-fill with the REAL LLM (before/after)

- New proof tool `tools/cfa/render_f3_tab_fill_withkey.py` calls
  `aqt.cfa_tab_fill.fill_note_back(note)` with NO injected `complete_fn`, so the
  default real `cfa.ai.llm_client.complete` path runs. It asserts `res["ok"]`,
  `res["status"] == "filled"`, and `ai-generated in note.tags`.
- The AFTER back is a genuine, run-to-run-varying LLM draft (this run:
  `gpt-4o-mini`, 369 chars, a correct Standard III(B) fair-dealing answer) — never
  hardcoded. BEFORE makes no LLM call (front filled, back empty, button enabled).
- Evidence: `proof/fixes/p4/f3-withkey-before.png`, `proof/fixes/p4/f3-withkey-after.png`
  (+ the `.html` sources; the after HTML embeds the real drafted text).

### Part 3 — AI-off fallback still works with the key ABSENT

- With `.env` moved aside (`.env.withkey.bak`, gitignored via item 1) and
  `OPENAI_API_KEY` unset: `just cfa-tab-fill-test` = **18/18 pass**, including
  `test_fill_note_back_ai_off_leaves_note_untouched`.
- `just cfa-ethics-eval` (exit 0) then reports `active grader : deterministic
  fallback (AI OFF)`, agreement **0.733**, and the LLM `>= 0.80` assertion is
  SKIPPED — the honest AI-off number. `.env` was restored afterward.
- Evidence: `proof/fixes/p4/f2-aioff-eval.txt`.

Verify (AI-off unaffected): no product code changed — only a new proof/render tool
under `tools/cfa/` and evidence under `proof/fixes/p4/`. The key copy is removed
from the worktree at the end of this item (`rm -f .env .env.withkey.bak`); the
shared checkout's `.env` is never touched.

---

## Item 5 — submission proof (SUBMISSION PROOF)

- Branch: `p4/05-submission` (stacked on `p4/04-withkey`, which contains items 1–4)
- Commit SHA (artifacts): `360529750ab9b6bec8938edbcf3550f870e2ede4`
- Commit SHA (this NOTES entry): _recorded via `git log` on the branch (the follow-up commit)_
- Gate: DEFERRED — `no-mistakes` intentionally NOT run for this item.

Closed the final engineering-quality gap: the headline evidence (test counts +
screenshots) was accounting/prose, not one-command reproducible; the real
live-app captures were untracked; and nothing tied the Brainlift POVs to shipped
features with evidence. All work is additive (`proof/**`, `demo/**`, `justfile`
recipe, `proof/gnhf2/f9-demo.html`, root `SUBMISSION-CHECKLIST.md`); no product
code, `docs/**`, or P1/P2 files were touched.

### Artifacts produced

- `demo/contact-sheet.png` (3336×4200 retina) + `demo/contact-sheet.html` — a
  clean labeled contact sheet built ONLY from real live-app captures (6 desktop
  macOS Anki panels + 4 AnkiDroid on-device panels) plus one real frame extracted
  from `demo/desktop-review.mp4` (ffmpeg @14s). Banner: "LIVE APP CAPTURE — real
  macOS Anki + AnkiDroid (not HTML/offscreen renders)".
- `proof/fixes/p4/BRAINLIFT.md` — the three spiky POVs (verbatim) → shipped
  features → concrete evidence, with honest caveats.
- `proof/fixes/p4/5-submission-before.txt`, `5-submission-after.txt` — the gap
  writeups (A/E).
- `proof/fixes/p4/f9-tally-before.txt`, `f9-tally-after.log` — the tally
  before/after with exact commands (D).
- `proof/fixes/p4/contact-src/` — the recovered real captures kept as evidence,
  plus two cropped panels (`03-cfa-menu-crop`, `06-priority-crop`) and the
  extracted `desktop-review-frame.png`.

### Reproducible tally (real numbers, one command each)

- Python/Qt: **203 passed, 1 skipped** (204 collected; the 1 skip is the with-key
  real-LLM smoke) via the new recipe `just cfa-f9-test-tally` — ONE deduplicated
  pytest collection using `--import-mode=importlib` with pylib tests listed first
  (so the four `tests` packages coexist and `tests.shared` binds to pylib/tests).
- Rust: **21** = 10 + 11 via two DISJOINT scoped filters:
  `cargo test -p anki --lib -- scheduler::cfa_deadline` (10) and
  `cargo test -p anki --lib -- scheduler::service::tests::exam_queue scheduler::service::tests::verification_probe` (11).
  The broad `-- exam` filter mis-reports 15 (it also matches the cfa_deadline test
  `exam_in_the_past_caps_all_intervals_at_zero`); the two scoped filters are
  disjoint, so 10+11 is the honest total.
- Updated to cite these exact commands: `justfile` (new recipe),
  `proof/gnhf2/f9-demo.html` (headline), root `SUBMISSION-CHECKLIST.md`
  (reproduce section + Real numbers). NOTE: `proof/gnhf2/f9-demo.png` was NOT
  re-rendered — the numbers are unchanged (203/1 + 21); only the HTML source
  gained the reproducibility citation, and `demo/contact-sheet.png` already
  carries it visually.

### Honest caveats

- Two source captures (`22-ethics-minpair-front`, `23-ethics-study-result`) do
  NOT depict the ethics card UI (22 = the deck list; 23 = an empty-state "CFA:
  Ethics Pairs deck is not available in this build" dialog), so they were kept as
  evidence but NOT put on the sheet as ethics panels; the live ethics experience
  is shown on-device (panels 8–10). Stated on the sheet footer too.
- Real committed videos: `demo/desktop-review.mp4` (45s desktop review — source of
  the contact-sheet frame) + `demo/build.mp4` (build timelapse). Still pending
  (environmental — needs a live device + installer fleet): `demo/phone-review.mp4`,
  `demo/install.mp4`.
- AI is OFF by default and every feature works without a key; F4 readiness is not
  validated against real exam outcomes; mobile = the shared fork Rust engine +
  synced content, not a full desktop port; all deck items are authored-original.
- Security: no `OPENAI_API_KEY` printed or committed; the staged-file scrub
  `git diff --cached --name-only | xargs grep -nE 'sk-(proj-)?[A-Za-z0-9_-]{20,}'`
  (and a byte-level Python re-scan of all 26 staged files) came back clean.
