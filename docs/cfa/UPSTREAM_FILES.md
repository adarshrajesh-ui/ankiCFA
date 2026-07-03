# Upstream surface: what this fork touches

_CFA Level II fork of Anki (AGPL-3.0-or-later). No AI features._

This is the complete, standalone list of every **upstream (stock-Anki) file the
fork modifies** and every **new fork-only file** it adds. It is derived from real
git data, not from notes:

- Fork divergence point (last stock-Anki commit): `6770ad3ef` — _"fix: Update
  allowed origins for recent Chromium (#5080)"_.
- Baseline being submitted: `b431cb1265f81abe8e18eff9c8839f3a25aae665` (branch `main`).
- Feature commits: `a0001ff11` (exam-prep queue engine + honest memory score) and
  `78f9bfb40` (Ethics Contrastive Minimal-Pairs).
- Plus uncommitted working-tree edits present at submission time.

Derivation commands (read-only):

```bash
git log --oneline --graph 6770ad3ef..b431cb126   # topology of the fork commits
git show --name-status a0001ff11                  # engine + memory-score commit
git show --name-status 78f9bfb40                  # ethics minimal-pairs commit
git diff --name-status 6770ad3ef b431cb126        # net committed fork surface
git diff --stat                                   # uncommitted working-tree edits
```

---

## 1. Modified upstream files (real stock-Anki files the fork edits)

These files exist in vanilla Anki and are the fork's **merge surface** — the only
places a future rebase onto upstream could conflict.

| Upstream file                        | Where                     | One-line change                                                                                                                                                                                                      |
| ------------------------------------ | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `proto/anki/scheduler.proto`         | `a0001ff11`               | Additive `+1 rpc BuildExamQueue` on `SchedulerService` and `+2` messages (`BuildExamQueueRequest`, `BuildExamQueueResponse`), appended after `FuzzDelta` — no field-number/wire-compat break.                        |
| `rslib/src/scheduler/service/mod.rs` | `a0001ff11` + uncommitted | Read-only `Collection::build_exam_queue` (trait method + inherent impl) with 3 private scoring helpers and unit tests; scores due cards by `topic_weight × (1 − retrievability) × deadline_urgency`, writes nothing. |
| `pylib/anki/scheduler/v3.py`         | `a0001ff11` + uncommitted | Thin `build_exam_queue(...)` wrapper over the generated backend binding (one new method in its own section).                                                                                                         |
| `qt/aqt/main.py`                     | `a0001ff11`               | 5 lines: `import aqt.cfa` + `aqt.cfa.setup_menu(self)` to add the top-level **CFA** menu during main-window setup.                                                                                                   |
| `justfile`                           | `78f9bfb40`               | 5 additive recipes for the ethics feature (`cfa-validate`, `cfa-test`, `cfa-import`, `cfa-dashboard`, `cfa-install-addon`) plus `py` / `cfa_env` variables.                                                          |
| `CONTRIBUTORS`                       | `a0001ff11`               | +1 line adding the fork author to the contributors list.                                                                                                                                                             |
| `README.md`                          | `a0001ff11`               | +38 lines: fork intro / CFA section. **(Owned by another agent — listed here for completeness, not edited by this doc.)**                                                                                            |

> The task named three known upstream-modified files (`scheduler.proto`,
> `service/mod.rs`, `v3.py`). All three are confirmed above; the additional
> upstream files found are `qt/aqt/main.py`, `justfile`, `CONTRIBUTORS`, and
> `README.md`.

### Uncommitted working-tree edits (on top of the baseline, present at submission)

| File                                                | Status                 | One-line change                                                                                                                                                                                                                                                  |
| --------------------------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rslib/src/scheduler/service/mod.rs`                | modified (uncommitted) | Exam queue now also includes **new (never-reviewed) cards** — treated as maximally weak (R = 0) so they rise naturally; adds an `add_new_card` test helper and 2 tests (`exam_queue_includes_new_cards`, `exam_queue_mixes_new_and_due_cards`). Still read-only. |
| `pylib/anki/scheduler/v3.py`                        | modified (uncommitted) | Docstring refinement: queue returns studyable cards (due review/learning **plus** new cards).                                                                                                                                                                    |
| `proof/.commit`, `proof/GATE.md`, `proof/README.md` | modified (uncommitted) | Fork-only proof artifacts (not upstream files; owned by the proof/coordinator agents).                                                                                                                                                                           |

Read-only preservation note: the uncommitted edits in `rslib/.../mod.rs` and
`pylib/.../v3.py` were **read/diffed only** for this doc and left untouched.

---

## 2. New fork-only files (no upstream merge surface)

These files do not exist in stock Anki, so upstream will never touch them — all
heavier CFA logic lives here to keep the merge surface tiny.

### Exam-prep engine, memory score, app & tooling (`a0001ff11`)

- `pylib/anki/cfa.py` — exam config (date + `los::` topic weights, persisted via
  collection config so it syncs natively) and the **honest per-topic memory
  score**: FSRS retrievability reported as a range with an enforced give-up rule.
- `qt/aqt/cfa.py` — the **CFA → Exam Readiness** desktop dialog.
- `pylib/tests/test_cfa.py` — 10 Python end-to-end tests (RPC + memory score).
- `tools/cfa/build_cfa_deck.py` — CFA Level II deck builder (`los::topic::reading` tags).
- `dist/launch-ankiCFA.sh` — clean-machine venv + launch script.

### Ethics Contrastive Minimal-Pairs (`78f9bfb40`) — all under `cfa/ethics_pairs/`

- `cfa/ethics_pairs/__init__.py`, `README.md`, `manifest.json`, `pairs.jsonl`
- `cfa/ethics_pairs/ethics_scoring.py`, `ethics_dashboard.py`, `ethics_notetype.py`,
  `ethics_revlog.py`, `import_pairs.py`
- `cfa/ethics_pairs/templates/front.html`, `back.html`, `style.css`
- `cfa/ethics_pairs/tests/test_ethics_scoring.py`, `test_dashboard.py`, `test_import_pairs.py`
- `ts/tests/e2e/ethics_pairs_flow.test.ts` — Playwright e2e flow test. _(New file
  placed inside the upstream `ts/tests/e2e/` directory but fork-authored; no
  upstream merge surface.)_

### Docs & proof (fork-only)

- `docs/cfa/RUST_ENGINE_NOTE.md`, `docs/cfa/PACKAGING.md` — design/packaging notes.
  **(Owned by other agents.)**
- `docs/cfa/UPSTREAM_FILES.md`, `docs/cfa/DEMO_SCRIPT.md` — this file and the demo script.
- `docs/prd/PRD.md` — root PRD index (`e7d3b881c`).
- `proof/` — `BASELINE.md`, `GATE.md`, `README.md`, `.commit`, and the `*.log`
  build/test/clippy/complexity/perf artifacts.

### Untracked working-tree items (present, not yet committed)

- `dist/build_cfa_deck.py`, `dist/anki-venv/`, `dist/wheels/` — local build/deck
  outputs (not part of the source surface).

---

## 3. Generated code is NOT counted as a modified upstream file

The following are **regenerated from `proto/anki/scheduler.proto`** by the build's
codegen — they are not hand edits and must not be treated as fork modifications:

- everything under `out/…`
- `pylib/anki/_backend_generated.py` (generated Python backend bindings)
- `out/ts/lib/generated/backend.ts` (generated TypeScript backend bindings)
- the Rust service trait/dispatch glue derived from the proto

Only the source `proto/anki/scheduler.proto` change (Section 1) is a real edit;
the bindings above simply follow from it.

---

## 4. Summary counts

- **Modified upstream files:** 7 committed (`scheduler.proto`, `service/mod.rs`,
  `v3.py`, `main.py`, `justfile`, `CONTRIBUTORS`, `README.md`) — of which
  `service/mod.rs` and `v3.py` also carry uncommitted edits.
- **New fork-only files:** the `cfa.py` / `aqt/cfa.py` / tests / tooling set, the
  full `cfa/ethics_pairs/` package (+ one `ts/` e2e test), plus docs and `proof/`.
- **Merge risk:** low — the proto change is purely additive and every heavy piece
  of logic lives in new files. See `docs/cfa/RUST_ENGINE_NOTE.md` for the Rust
  merge-difficulty analysis.
